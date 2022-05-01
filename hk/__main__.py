from .models.bot import Bot
import asyncio

async def main():
    bot = Bot(settings='settings.yaml')
    await bot.start()

try:
    asyncio.run(main())
except KeyboardInterrupt:
    exit()