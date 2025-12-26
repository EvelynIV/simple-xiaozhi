from __future__ import annotations

from dataclasses import dataclass
import os

from simple_xiaozhi.utils.config_manager import ConfigManager


@dataclass(frozen=True)
class ClientSettings:
    ws_url: str
    access_token: str
    device_id: str
    client_id: str


def _env(name: str) -> str | None:
    value = os.getenv(name)
    return value if value else None


def load_settings() -> ClientSettings:
    config = ConfigManager.get_instance()

    ws_url = _env("XIAOZHI_WS_URL") or config.get_config(
        "SYSTEM_OPTIONS.NETWORK.WEBSOCKET_URL"
    )
    access_token = _env("XIAOZHI_ACCESS_TOKEN") or config.get_config(
        "SYSTEM_OPTIONS.NETWORK.WEBSOCKET_ACCESS_TOKEN"
    )
    device_id = _env("XIAOZHI_DEVICE_ID") or config.get_config(
        "SYSTEM_OPTIONS.DEVICE_ID"
    )
    client_id = _env("XIAOZHI_CLIENT_ID") or config.get_config(
        "SYSTEM_OPTIONS.CLIENT_ID"
    )

    missing = [
        name
        for name, value in [
            ("WEBSOCKET_URL", ws_url),
            ("WEBSOCKET_ACCESS_TOKEN", access_token),
            ("DEVICE_ID", device_id),
            ("CLIENT_ID", client_id),
        ]
        if not value
    ]
    if missing:
        raise ValueError(f"Missing config values: {', '.join(missing)}")

    return ClientSettings(
        ws_url=str(ws_url),
        access_token=str(access_token),
        device_id=str(device_id),
        client_id=str(client_id),
    )
