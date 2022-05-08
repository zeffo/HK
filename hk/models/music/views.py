from __future__ import annotations
from discord.ui import View, Select, Button
from discord import SelectOption, Interaction
from ..context import Context
from .track import ResultsType


class Dropdown(Select['MediaPlayer']):
    def __init__(self, tracks: ResultsType):
        options = [SelectOption(label=t.title[:100], description=f"by {t.uploader[:90]}", value=t.id) for t in tracks]
        options[0].default = True
        super().__init__(options=options)

    async def callback(self, interaction: Interaction):
        if self.view:
            await self.view.render(interaction)

class Submit(Button['MediaPlayer']):
    def __init__(self):
        super().__init__(label='Submit')
    async def callback(self, interaction: Interaction):
        if self.view:
            await self.view.render(interaction)


class MediaPlayer(View):
    def __init__(self, ctx: Context, tracks: ResultsType):
        super().__init__()
        self.ctx = ctx
        self.tracks = {t.id: t for t in tracks}
        self.dropdown = Dropdown(tracks)
        self.add_item(self.dropdown)
        # self.add_item(Submit())

    async def render(self, interaction: Interaction):
        track = self.tracks[self.dropdown.values[0]]
        embed = track.embed()
        embed.color = self.ctx.bot.conf.color
        await interaction.response.edit_message(embed=embed)
    