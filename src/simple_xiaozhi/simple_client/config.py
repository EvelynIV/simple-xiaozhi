from __future__ import annotations

from dataclasses import dataclass

from simple_xiaozhi.utils.config_manager import ConfigManager


@dataclass(frozen=True)
class ClientSettings:
    ws_url: str
    access_token: str
    device_id: str
    client_id: str


def load_settings() -> ClientSettings:
    config = ConfigManager.get_instance()

    ws_url = config.get_config("SYSTEM_OPTIONS.NETWORK.WEBSOCKET_URL")
    access_token = config.get_config("SYSTEM_OPTIONS.NETWORK.WEBSOCKET_ACCESS_TOKEN")
    device_id = config.get_config("SYSTEM_OPTIONS.DEVICE_ID")
    client_id = config.get_config("SYSTEM_OPTIONS.CLIENT_ID")

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
