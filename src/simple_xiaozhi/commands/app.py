import typer
import asyncio
from pathlib import Path

from simple_xiaozhi.simple_client import SimpleClientApp
from simple_xiaozhi.utils.config_manager import ConfigManager
from simple_xiaozhi.utils.logging_config import setup_logging

app = typer.Typer()

async def _run_simple_client() -> None:
    client_app = SimpleClientApp()
    try:
        await client_app.run()
    except asyncio.CancelledError:
        await client_app.close()
        raise


@app.command()
def simple_client(
    config_dir: Path = typer.Argument(
        "model-bin",
        envvar="SIMPLE_XIAOZHI_CONFIG_DIR",
        help="The config directory for simple xiaozhi client.",
    ),
    ws_url: str | None = typer.Option(
        None,
        "--ws-url",
        envvar="XIAOZHI_WS_URL",
        help="Override websocket URL.",
    ),
    access_token: str | None = typer.Option(
        None,
        "--access-token",
        envvar="XIAOZHI_ACCESS_TOKEN",
        help="Override websocket access token.",
    ),
    device_id: str | None = typer.Option(
        None,
        "--device-id",
        envvar="XIAOZHI_DEVICE_ID",
        help="Override device id.",
    ),
    client_id: str | None = typer.Option(
        None,
        "--client-id",
        envvar="XIAOZHI_CLIENT_ID",
        help="Override client id.",
    ),
):
    setup_logging()

    overrides: dict = {}
    system_overrides: dict = {}
    network_overrides: dict = {}
    if ws_url:
        network_overrides["WEBSOCKET_URL"] = ws_url
    if access_token:
        network_overrides["WEBSOCKET_ACCESS_TOKEN"] = access_token
    if network_overrides:
        system_overrides["NETWORK"] = network_overrides
    if device_id:
        system_overrides["DEVICE_ID"] = device_id
    if client_id:
        system_overrides["CLIENT_ID"] = client_id
    if system_overrides:
        overrides["SYSTEM_OPTIONS"] = system_overrides

    ConfigManager.get_instance(config_dir=config_dir, overrides=overrides)
    try:
        asyncio.run(_run_simple_client())
    except KeyboardInterrupt:
        pass


def main():
    app()


if __name__ == "__main__":
    app()
