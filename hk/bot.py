from __future__ import annotations

import sys
import traceback
from pathlib import Path
from textwrap import dedent
from typing import Any

from aiohttp import ClientSession
from colorama import Fore
from discord import Intents
from discord.ext import commands

from .settings import Config
from . import __version__


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

        await self.tree.sync()

    async def on_ready(self):
        print(
            dedent(
                f"""
            {Fore.RED}
             __    __   __  ___ 
            |  |  |  | |  |/  / 
            |  |__|  | |  '  /  
            |   __   | |    <   
            |  |  |  | |  .  \\  
            |__|  |__| |__|\\__\\
            
            Version {__version__}
            {Fore.RESET}        
            Guilds: {len(self.guilds)}
            Users: {len(self.users)}
            Commands: {len(self.tree.get_commands())}
            Extensions: {len(self.extensions)}
            Cogs: {len(self.cogs)}
            """
            )
        )
