import asyncio


from simple_xiaozhi.simple_client import SimpleClientApp
from simple_xiaozhi.utils.logging_config import setup_logging


async def main() -> None:
    app = SimpleClientApp()
    await app.run()


if __name__ == "__main__":
    setup_logging()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
