from __future__ import annotations

import asyncio
from typing import Awaitable, Callable

from websockets.exceptions import ConnectionClosed

from simple_xiaozhi.utils.logging_config import get_logger
from simple_xiaozhi.utils.opus_loader import setup_opus

setup_opus()

from simple_xiaozhi.audio_codecs.audio_codec import AudioCodec

logger = get_logger(__name__)


class AudioPipeline:
    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop
        self._codec: AudioCodec | None = None
        self._queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=200)
        self._sender: Callable[[bytes], Awaitable[None]] | None = None
        self._sender_task: asyncio.Task | None = None
        self._running = False
        self._send_enabled = False

    async def start(self, sender: Callable[[bytes], Awaitable[None]]) -> None:
        self._sender = sender
        self._codec = AudioCodec()
        await self._codec.initialize()
        self._codec.set_encoded_callback(self._on_encoded)
        self._running = True
        self._sender_task = asyncio.create_task(self._sender_loop())

    async def stop(self) -> None:
        self._running = False
        self._send_enabled = False
        if self._sender_task and not self._sender_task.done():
            self._sender_task.cancel()
            try:
                await self._sender_task
            except asyncio.CancelledError:
                pass
        self._sender_task = None
        if self._codec:
            await self._codec.close()
            self._codec = None

    def enable_sending(self, enabled: bool) -> None:
        self._send_enabled = enabled

    async def handle_incoming_audio(self, data: bytes) -> None:
        if self._codec:
            await self._codec.write_audio(data)

    def _on_encoded(self, data: bytes) -> None:
        if not self._running or not self._send_enabled:
            return
        try:
            self._loop.call_soon_threadsafe(self._enqueue, data)
        except RuntimeError:
            pass

    def _enqueue(self, data: bytes) -> None:
        if not self._running:
            return
        try:
            self._queue.put_nowait(data)
        except asyncio.QueueFull:
            logger.debug("Audio queue full, dropping frame")

    async def _sender_loop(self) -> None:
        if not self._sender:
            return
        while self._running:
            try:
                data = await self._queue.get()
                await self._sender(data)
            except asyncio.CancelledError:
                break
            except ConnectionClosed as exc:
                # 服务端主动断开连接是预期行为，停止发送循环
                logger.info("Audio send stopped: connection closed (%s)", exc.code)
                self._send_enabled = False
                break
            except Exception as exc:
                logger.warning("Audio send failed: %s", exc)
