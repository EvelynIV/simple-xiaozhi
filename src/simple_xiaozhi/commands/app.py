import typer
import asyncio
from pathlib import Path

from simple_xiaozhi.simple_client import SimpleClientApp
from simple_xiaozhi.utils.config_manager import ConfigManager
from simple_xiaozhi.utils.logging_config import setup_logging

app = typer.Typer()


@app.command()
def simple_client(
    config_dir: Path = typer.Argument(
        "model-bin",
        envvar="SIMPLE_XIAOZHI_CONFIG_DIR",
        help="The config directory for simple xiaozhi client.",
    )
):
    setup_logging()

    ConfigManager.get_instance(config_dir=config_dir)
    app = SimpleClientApp()
    asyncio.run(app.run())


def main():
    app()


if __name__ == "__main__":
    app()
