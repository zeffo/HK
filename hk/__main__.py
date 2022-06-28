from .bot import Bot
from .settings import Config
import asyncio
import logging
import logging.handlers

logger = logging.getLogger("discord")
logger.setLevel(logging.ERROR)
logging.getLogger("discord.http").setLevel(logging.INFO)

handler = logging.handlers.RotatingFileHandler(
    filename="discord.log",
    encoding="utf-8",
    maxBytes=32 * 1024 * 1024,  # 32 MiB
    backupCount=5,  # Rotate through 5 files
)
dt_fmt = "%Y-%m-%d %H:%M:%S"
formatter = logging.Formatter(
    "[{asctime}] [{levelname:<8}] {name}: {message}", dt_fmt, style="{"
)
handler.setFormatter(formatter)
logger.addHandler(handler)


async def main():
    bot = Bot(Config())
    await bot.start()


try:
    asyncio.run(main())
except KeyboardInterrupt:
    exit()
