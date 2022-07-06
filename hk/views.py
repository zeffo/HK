from __future__ import annotations
from discord import ButtonStyle, Embed, File, Interaction
from discord.ui import View, button, Button
from .music import Payload, Queue
from .bot import Bot
from typing import Optional, List
from copy import deepcopy


class Unit:
    __slots__ = ('content', 'embed', '_files')
    def __init__(self, *, content: Optional[str]=None, embed: Optional[Embed]=None, files: Optional[List[File]]=None):
        self.content = content
        self.embed = embed
        self._files = files or []

    @property
    def files(self):
        """Returns a list of deepcopies of the original files for reusability"""
        return [deepcopy(f) for f in self._files]

class Paginator(View):
    def __init__(self, bot: Bot, *items: Unit):
        super().__init__()
        self.bot = bot
        self.items = items
        self.page = 0

        for child in self.children:
            if isinstance(child, Button):
                if child.style == ButtonStyle.secondary:
                    child.style = ButtonStyle.primary
                child.emoji = self.bot.conf.emojis[child.callback.callback.__name__]    # type: ignore (child.callback isinstance _ViewCallback here)

    async def edit(self, iact: Interaction, *, page: int):
        self.page = page
        unit = self.items[page]
        await iact.response.edit_message(content=unit.content, embed=unit.embed, attachments=unit.files)
    
    @button()
    async def first(self, iact: Interaction, button: Button[Paginator]):
        await self.edit(iact, page=0)

    @button()
    async def back(self, iact: Interaction, button: Button[Paginator]):
        await self.edit(iact, page=max(self.page-1, 0))
    
    @button()
    async def next(self, iact: Interaction, button: Button[Paginator]):
        await self.edit(iact, page=min(self.page+1, len(self.items)-1))
    
    @button()
    async def skip(self, iact: Interaction, button: Button[Paginator]):
        await self.edit(iact, page=len(self.items)-1)
    
