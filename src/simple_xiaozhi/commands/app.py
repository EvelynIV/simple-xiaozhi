import typer
import asyncio


from simple_xiaozhi.simple_client import SimpleClientApp
from simple_xiaozhi.utils.logging_config import setup_logging

app = typer.Typer()


@app.command()
def simple_client():
    setup_logging()

    app = SimpleClientApp()
    asyncio.run(app.run())


def main():
    app()


if __name__ == "__main__":
    app()
