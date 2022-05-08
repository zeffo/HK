from __future__ import annotations
from discord.ext import commands
from discord import Intents, AllowedMentions, Message
from typing import Any
import asyncio
import traceback
import sys
from pathlib import Path
import aiohttp

from .settings import Settings
from .context import Context
from .database import Client

from ..utils.sysinfo import sysinfo


class Bot(commands.Bot):
    def __init__(self, *args: Any, settings: str, **kwargs: Any):
        self.conf = Settings(settings)
        self.session = aiohttp.ClientSession()
        self.db = Client(self.conf.postgres_uri, loop=asyncio.get_running_loop())
        _intents = Intents._from_value(self.conf.intents)  # type: ignore

        super().__init__(
            command_prefix=self.conf.prefix,
            intents=_intents,
            allowed_mentions=AllowedMentions(everyone=False),
            *args,
            **kwargs
        )

    def __getitem__(self, item: Any) -> Any:
        return getattr(self.conf, item)

    async def on_message(self, message: Message):
        if message.author.bot:
            return
        ctx = await self.get_context(message, cls=Context)
        await self.invoke(ctx)

    async def load_extensions(self) -> None:
        """Loads the extensions in the configuration file"""
        for file in Path("hk/ext").glob("**/*.py"):
            *tree, _ = file.parts
            try:
                await self.load_extension(f"{'.'.join(tree)}.{file.stem}")
            except Exception as e:
                traceback.print_exception(type(e), e, e.__traceback__, file=sys.stderr)
        for ex in self.conf.extensions:
            await self.load_extension(ex)

    async def start(self):
        await self.db.prepare()
        await self.load_extensions()
        await super().start(token=self.conf.discord_api_token)

    async def on_ready(self):
        print(sysinfo(self))

