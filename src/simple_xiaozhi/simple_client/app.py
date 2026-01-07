from __future__ import annotations

import asyncio
from typing import Any

from simple_xiaozhi.simple_client.audio import AudioPipeline
from simple_xiaozhi.simple_client.config import ClientSettings, load_settings
from simple_xiaozhi.simple_client.ws_client import WebSocketClient
from simple_xiaozhi.utils.logging_config import get_logger

logger = get_logger(__name__)


class SimpleClientApp:
    def __init__(self, settings: ClientSettings | None = None) -> None:
        self._settings = settings or load_settings()
        self._ws: WebSocketClient | None = None
        self._audio: AudioPipeline | None = None
        self._stop_event = asyncio.Event()

    async def run(self) -> None:
        try:
            loop = asyncio.get_running_loop()
            self._ws = WebSocketClient(self._settings)
            self._ws.on_json(self._handle_json)
            self._ws.on_audio(self._handle_audio)
            self._ws.on_close(self._handle_close)
            await self._ws.connect()
            await self._ws.handshake()

            self._audio = AudioPipeline(loop)
            await self._audio.start(self._ws.send_audio)
            await self._ws.start_listening(mode="realtime")
            self._audio.enable_sending(True)

            await self._stop_event.wait()
        except asyncio.CancelledError:
            pass
        finally:
            await self.close()

    async def close(self) -> None:
        if self._audio:
            await self._audio.stop()
            self._audio = None
        if self._ws:
            try:
                await self._ws.send_json({"type": "listen", "state": "stop"})
            except Exception:
                pass
            await self._ws.close()
            self._ws = None

    async def _handle_audio(self, data: bytes) -> None:
        if self._audio:
            await self._audio.handle_incoming_audio(data)

    async def _handle_close(self) -> None:
        """处理服务端断开连接"""
        logger.info("Server disconnected, stopping client")
        self._stop_event.set()

    async def _handle_json(self, data: dict) -> None:
        msg_type = data.get("type")
        if msg_type in ("stt", "tts"):
            print(f"[{msg_type}] {data}")
            # 处理 TTS 事件，控制音频缓存
            if msg_type == "tts" and self._audio and self._audio._codec:
                state = data.get("state")
                if state == "start":
                    self._audio._codec.start_tts_cache()
                elif state == "stop":
                    self._audio._codec.end_tts_cache()
            return
        if msg_type == "llm":
            # emotion = data.get("emotion")
            # if emotion:
            print(f"[llm] {data}")
            return
        if msg_type == "hello":
            print(f"[hello] {data}")
            return
        elif msg_type == "mcp":
            print(f"[mcp] {data}")
        if msg_type:
            print(f"[{msg_type}] {data}")
        else:
            print(f"[json] {data}")
