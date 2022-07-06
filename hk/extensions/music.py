from __future__ import annotations

from typing import (TYPE_CHECKING, Any, Dict, Union)

from discord import (ButtonStyle, Embed, Guild, Interaction, SelectOption,
                     app_commands)
from discord.ext import commands
from discord.ui import Button, Select, View

from ..music import (YTDL, BasePlaylist, BaseTrack, Payload,
                     Queue)

if TYPE_CHECKING:
    from ..bot import Bot

class BaseMusicView(View):
    payload: Payload
    async def interaction_check(self, interaction: Interaction) -> bool:
        return self.payload.interaction.user == interaction.user
        
class CancelButton(Button[View]):
    def __init__(self):
        super().__init__(style=ButtonStyle.danger, label="Cancel")

    async def callback(self, interaction: Interaction) -> Any:
        if message := interaction.message:
            await message.delete()


class TrackSelect(Select['PlayView']):
    def __init__(self, *items: Union[BaseTrack, BasePlaylist]):
        self.items = items
        self.page = 0 
        options = [SelectOption(label=t.title, value=str(i), description=f"By {t.uploader}") for i, t in enumerate(items)]
        options[0].default = True
        super().__init__(options=options)
        self._selected_values = ["0"]
    
    async def callback(self, interaction: Interaction) -> Any:
        idx = int(self.values[0])
        track = self.items[idx]
        self.options[idx].default = True
        self.options[self.page].default = False
        self.page = idx
        self._selected_values = [str(idx)]
        if self.view is not None:
            banner = await track.create_banner(self.view.payload.bot.session)
            embed = banner.embed()
            await interaction.response.edit_message(embed=embed.set_footer(text=f"{track.title}\nby {track.uploader}"), attachments=[banner.file()], view=self.view)

class PlayView(View):
    def __init__(
        self,
        payload: Payload,
        queue: Queue,
        *items: Union[BaseTrack, BasePlaylist],
    ):
        super().__init__()
        self.payload = payload
        self.queue = queue
        self.select = TrackSelect(*items)
        enqueue: Button["PlayView"] = Button(
            style=ButtonStyle.primary, label="Add to Queue"
        )
        enqueue.callback = self.enqueue
        self.add_item(self.select)
        self.add_item(enqueue)
        self.add_item(CancelButton())

    @classmethod
    async def display(cls, payload: Payload, queue: Queue, query: str):
        items = await YTDL.from_query(
            query, session=payload.bot.session, api_key=payload.bot.conf.env["YOUTUBE"]
        )
        head = items[0]
        banner = await head.create_banner(payload.bot.session)
        embed = banner.embed()
        embed.set_footer(text=f"{head.title}\nby {head.uploader}\n{len(head.entries) if isinstance(head, BasePlaylist) else ''}")
        await payload.interaction.followup.send(
            embed=embed, file=banner.file(), ephemeral=True, view=cls(payload, queue, *items)
        )
    
    async def enqueue(self, interaction: Interaction):
        if message := interaction.message:
            if self.queue.qsize() == 0 and not self.queue.lock.locked():
                await message.delete()
            else:
                embed = interaction.message.embeds[0]
                embed.set_footer(text="Queued\n" + str(embed.footer.text))
                await interaction.response.edit_message(view=None, embed=embed, attachments=message.attachments)
        track = self.select.items[int(self.select.values[0])]
        await self.queue.put(track)


class Music(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.queues: Dict[Guild, Queue] = {}

    def get_queue(self, payload: Payload):
        return self.queues.setdefault(
            payload.guild, Queue(self.bot, bound=payload.channel)
        )

    @app_commands.command()
    async def play(self, iact: Interaction, query: str):
        """Play a song or playlist from YouTube"""
        await iact.response.defer()
        payload = await Payload.from_interaction(self.bot, iact)
        queue = self.get_queue(payload)
        await PlayView.display(payload, queue, query)

    @app_commands.command()
    async def pause(self, iact: Interaction):
        """Pause the current track"""
        payload = await Payload.from_interaction(self.bot, iact)
        payload.voice_client.pause()
        await iact.response.send_message(embed=Embed(description="Paused!", color=self.bot.conf.color))

    @app_commands.command()
    async def resume(self, iact: Interaction):
        """Resume the current track"""
        payload = await Payload.from_interaction(self.bot, iact)
        payload.voice_client.resume()
        await iact.response.send_message(embed=Embed(description="Resumed!", color=self.bot.conf.color))
    
    @app_commands.command()
    async def skip(self, iact: Interaction):
        """Skip the current track"""
        payload = await Payload.from_interaction(self.bot, iact)
        queue = self.get_queue(payload)
        if np := queue.lock.track:
            banner = await np.create_banner(self.bot.session)
            embed = banner.embed()
            embed.description = "Skipping"
            embed.set_footer(text=np.title, icon_url=np.get_thumbnail())
            payload.voice_client.stop()
        else:
            embed = Embed(description="Nothing to skip!", color=self.bot.conf.color)
        await iact.response.send_message(embed=embed)

async def setup(bot: Bot):
    await bot.add_cog(Music(bot))
