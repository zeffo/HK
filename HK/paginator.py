import inspect
from discord.ui import View, button
from discord.ext import commands
from discord import ButtonStyle, Emoji, Interaction, InteractionMessage, PartialEmoji
from typing import List, Union, Optional, Callable
from discord.ui.item import Item, ItemCallbackType


class Unit(dict):
    def __getattr__(self, attr):
        try:
            return super().__getattr__(attr)
        except AttributeError:
            return self.get(attr)

    async def edit(self, message):
        await message.edit(content=self.content, embed=self.embed)


class Paginator(View):
    def __init__(
        self,
        ctx: commands.Context,
        *,
        units: List[Unit],
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.ctx = ctx
        self.units = units
        self.cursor = 0

        for unit in units:
            if not unit.embed.color:
                unit.embed.color = ctx.bot.color

        for child in self.children:
            emoji = ctx.bot.settings["emojis"][child.callback.func.__name__]
            child.emoji = emoji

    async def move(self, idx: int, interaction: Interaction):
        self.cursor = idx
        await self.units[idx].edit(interaction.message)

    @button()
    async def first(self, btn, i):
        await self.move(0, i)

    @button()
    async def back(self, btn, i):
        if (pos := self.cursor - 1) >= 0:
            await self.move(pos, i)

    @button()
    async def stop(self, btn, i):
        super().stop()
        await i.message.delete()

    @button()
    async def next(self, btn, i):
        if (pos := self.cursor + 1) < len(self.units):
            await self.move(pos, i)

    @button()
    async def last(self, btn, i):
        await self.move(len(self.units) - 1, i)

    async def interaction_check(self, interaction):
        return interaction.user == self.ctx.author
