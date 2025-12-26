from __future__ import annotations

import asyncio
import json
import ssl
from typing import Awaitable, Callable

import websockets

from simple_xiaozhi.constants.constants import AudioConfig
from simple_xiaozhi.simple_client.config import ClientSettings
from simple_xiaozhi.utils.logging_config import get_logger

logger = get_logger(__name__)


class WebSocketClient:
    def __init__(self, settings: ClientSettings) -> None:
        self._settings = settings
        self._ws = None
        self._hello_event = asyncio.Event()
        self._receiver_task: asyncio.Task | None = None
        self._on_json: Callable[[dict], Awaitable[None]] | None = None
        self._on_audio: Callable[[bytes], Awaitable[None]] | None = None

    def on_json(self, callback: Callable[[dict], Awaitable[None]]) -> None:
        self._on_json = callback

    def on_audio(self, callback: Callable[[bytes], Awaitable[None]]) -> None:
        self._on_audio = callback

    async def connect(self) -> None:
        headers = {
            "Authorization": f"Bearer {self._settings.access_token}",
            "Protocol-Version": "1",
            "Device-Id": self._settings.device_id,
            "Client-Id": self._settings.client_id,
        }
        ssl_context = None
        if self._settings.ws_url.startswith("wss://"):
            ssl_context = ssl._create_unverified_context()

        try:
            self._ws = await websockets.connect(
                uri=self._settings.ws_url,
                ssl=ssl_context,
                additional_headers=headers,
                ping_interval=20,
                ping_timeout=20,
                close_timeout=10,
                max_size=10 * 1024 * 1024,
                compression=None,
            )
        except TypeError:
            self._ws = await websockets.connect(
                self._settings.ws_url,
                ssl=ssl_context,
                extra_headers=headers,
                ping_interval=20,
                ping_timeout=20,
                close_timeout=10,
                max_size=10 * 1024 * 1024,
                compression=None,
            )

        self._receiver_task = asyncio.create_task(self._receiver_loop())

    async def handshake(self) -> None:
        self._hello_event.clear()
        await self.send_json(
            {
                "type": "hello",
                "version": 1,
                "features": {"mcp": True},
                "transport": "websocket",
                "audio_params": {
                    "format": "opus",
                    "sample_rate": AudioConfig.INPUT_SAMPLE_RATE,
                    "channels": AudioConfig.CHANNELS,
                    "frame_duration": AudioConfig.FRAME_DURATION,
                },
            }
        )
        await asyncio.wait_for(self._hello_event.wait(), timeout=10.0)

    async def start_listening(self, mode: str = "realtime") -> None:
        await self.send_json(
            {
                "type": "listen",
                "state": "start",
                "mode": mode,
            }
        )

    async def send_json(self, payload: dict) -> None:
        if not self._ws:
            return
        await self._ws.send(json.dumps(payload))

    async def send_audio(self, data: bytes) -> None:
        if not self._ws:
            return
        await self._ws.send(data)

    async def close(self) -> None:
        if self._receiver_task and not self._receiver_task.done():
            self._receiver_task.cancel()
            try:
                await self._receiver_task
            except asyncio.CancelledError:
                pass
        self._receiver_task = None
        if self._ws:
            await self._ws.close()
            self._ws = None

    async def _receiver_loop(self) -> None:
        if not self._ws:
            return
        try:
            async for message in self._ws:
                if isinstance(message, str):
                    await self._handle_text(message)
                elif isinstance(message, bytes):
                    if self._on_audio:
                        await self._on_audio(message)
        except asyncio.CancelledError:
            return
        except Exception as exc:
            logger.warning("WebSocket receiver stopped: %s", exc)

    async def _handle_text(self, message: str) -> None:
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            logger.warning("Invalid JSON: %s", message)
            return

        if data.get("type") == "hello":
            self._hello_event.set()

        if self._on_json:
            await self._on_json(data)
