import aiohttp, asyncpg, asyncio
import sys
import traceback
import yaml
import logging
from os import getenv
from discord import AllowedMentions, Intents, Embed
from discord.ext import commands
from dotenv import load_dotenv
from pathlib import Path
from .utils import sysinfo

logger = logging.getLogger('discord')
logger.setLevel(logging.ERROR)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

load_dotenv()
with open("config.yaml") as f:
    settings = yaml.safe_load(f)


class Bot(commands.Bot):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.color = settings['color']
        default_emojis = {
            "first": "⏮️",
            "stop": "⏹️",
            "last": "⏭️",
            "next": "➡️",
            "back": "⬅️",
        }
        self.settings: dict = settings
        self.settings.setdefault('emojis', default_emojis)

    async def validate_tables(self):
        """Creates required tables"""
        async with self.pool.acquire() as con:
            await con.execute("CREATE TABLE IF NOT EXISTS Tags (keyword TEXT Primary Key, meta TEXT);")
        
    async def start(self) -> None:
        self.pool = await asyncpg.create_pool(getenv("DATABASE_URI"))
        await self.validate_tables()
        self._session = aiohttp.ClientSession()
        for file in Path('HK/extensions').glob('**/*.py'):
            *tree, _ = file.parts
            try:
                self.load_extension(f"{'.'.join(tree)}.{file.stem}")
            except Exception as e:
                traceback.print_exception(type(e), e, e.__traceback__, file=sys.stderr)
        for ex in self.settings.get('extensions', ()):
            self.load_extension(ex)
        await super().start(getenv("TOKEN"))

    async def stop(self):
        await self._session.close()
        await self.close()
        await self.loop.shutdown_asyncgens()

    async def on_ready(self):
        print(sysinfo(self))

    def embed(self, *args, **kwargs) -> Embed:
        if 'color' not in kwargs:
            kwargs['color'] = self.color
        return Embed(*args, **kwargs)

if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    bot = Bot(
        settings.get("prefix", "hk "),
        allowed_mentions=AllowedMentions(everyone=False),
        intents=Intents.all(),
        loop=loop,
    )

    try:
        loop.create_task(bot.start())
        loop.run_forever()
    except KeyboardInterrupt:
        loop.run_until_complete(bot.stop())
        exit(0)
