from __future__ import annotations

import sys
import traceback
from pathlib import Path
from typing import Any

from aiohttp import ClientSession
from discord import Intents, Object
from discord.ext import commands

from . import Config


class Bot(commands.Bot):
    conf: Config
    session: ClientSession

    def __init__(self, conf: Config, *args: Any, **kwargs: Any):
        super().__init__(command_prefix=conf.prefix, intents=Intents._from_value(conf.intents), *args, **kwargs)  # type: ignore
        self.conf = conf

    async def start(self, *args: Any, **kwargs: Any):
        self.session = ClientSession()
        return await super().start(self.conf.env["DISCORD"], *args, **kwargs)

    async def setup_hook(self) -> None:
        for file in Path("hk/extensions").glob("**/*.py"):
            *tree, _ = file.parts
            try:
                await self.load_extension(f"{'.'.join(tree)}.{file.stem}")
            except Exception as e:
                traceback.print_exception(type(e), e, e.__traceback__, file=sys.stderr)
        for ex in self.conf.extensions:
            await self.load_extension(ex)

        for guild in self.conf.debug_guilds or []:
            guild = self.get_guild(guild) or Object(guild)
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            print(
                f"Synced {len(synced)} command(s): {', '.join(c.name for c in synced)} to {getattr(guild, 'name', guild.id)}"
            )
