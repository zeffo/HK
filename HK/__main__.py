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
from typing import Optional

logger = logging.getLogger("discord")
logger.setLevel(logging.ERROR)
handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
handler.setFormatter(
    logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s")
)
logger.addHandler(handler)

load_dotenv()
with open("config.yaml") as f:
    settings = yaml.safe_load(f)


class Context(commands.Context):
    async def connect(self):
        if self.voice_client:
            return self.voice_client
        elif (vc := self.author.voice.channel):
            return await vc.connect()

    async def send(self, *args, **kwargs):
        if 'embed' in kwargs:
            kwargs['embed'].color = self.bot.color
        
        return await super().send(*args, **kwargs)
        

class Bot(commands.Bot):
    pool: Optional[asyncpg.pool.Pool] = None

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.color = settings["color"]
        default_emojis = {
            "first": "⏮️",
            "stop": "⏹️",
            "last": "⏭️",
            "next": "➡️",
            "back": "⬅️",
        }
        self.settings: dict = settings
        self.settings.setdefault("emojis", default_emojis)

    async def validate_tables(self):
        """Creates required tables"""
        if self.pool is None:
            raise ValueError("Bot has no connection pool!")
        async with self.pool.acquire() as con:
            await con.execute(
                "CREATE TABLE IF NOT EXISTS Tags (keyword TEXT Primary Key, meta TEXT);"
            )

    async def on_message(self, message):
        ctx = await self.get_context(message, cls=Context)
        await self.invoke(ctx)

    async def start(self) -> None:
        if uri := getenv("DATABASE_URI"):
            self.pool = await asyncpg.create_pool(uri)
            await self.validate_tables()
        self._session = aiohttp.ClientSession()
        for file in Path("HK/extensions").glob("**/*.py"):
            *tree, _ = file.parts
            try:
                self.load_extension(f"{'.'.join(tree)}.{file.stem}")
            except Exception as e:
                traceback.print_exception(type(e), e, e.__traceback__, file=sys.stderr)
        for ex in self.settings.get("extensions", ()):
            self.load_extension(ex)
        await super().start(getenv("TOKEN"))    #type: ignore

    async def stop(self):
        await self._session.close()
        await self.close()
        await self.loop.shutdown_asyncgens()

    async def on_ready(self):
        print(sysinfo(self))

    def embed(self, *args, **kwargs) -> Embed:
        if "color" not in kwargs:
            kwargs["color"] = self.color
        return Embed(*args, **kwargs)


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    bot = Bot(
        settings.get("prefix", "hk "),
        allowed_mentions=AllowedMentions(everyone=False),
        intents=Intents._from_value(settings.get('intents', 131071)),
        loop=loop,
    )

    try:
        loop.create_task(bot.start())
        loop.run_forever()
    except KeyboardInterrupt:
        loop.run_until_complete(bot.stop())
        exit(0)
