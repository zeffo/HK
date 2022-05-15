from __future__ import annotations

import sys
import traceback
from pathlib import Path
from typing import Any

import aiohttp
import prisma
from discord import AllowedMentions, Intents, Message, Object
from discord.ext import commands

from ..utils.sysinfo import sysinfo
from .context import Context
from .settings import Settings


class Bot(commands.Bot):
    def __init__(self, *args: Any, settings: str, **kwargs: Any):
        self.conf = Settings(settings)
        self.session = aiohttp.ClientSession()
        self.db = prisma.Prisma()

        self.debug_guild = Object(self.conf.debug_guild) if self.conf.debug_guild else None
        _intents = Intents._from_value(self.conf.intents)  # type: ignore
        super().__init__(
            command_prefix=self.conf.prefix,
            intents=_intents,
            allowed_mentions=AllowedMentions(everyone=False),
            application_id=self.conf.application_id,
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
        prisma.register(self.db)
        await self.load_extensions()
        await super().start(token=self.conf.discord_api_token)

    async def on_ready(self):
        print(sysinfo(self))

    async def setup_hook(self) -> None:
        synced = await self.tree.sync(guild=self.debug_guild)
        print(f"Synced {len(synced)} commands: {', '.join(c.name for c in synced)}")

