from __future__ import annotations

from typing import (TYPE_CHECKING, Any, Callable, Coroutine, Dict, Protocol,
                    Sequence, Tuple, Union, runtime_checkable)

from discord import (ButtonStyle, Embed, Guild, Interaction, Member,
                     SelectOption, VoiceChannel, VoiceClient, VoiceState,
                     app_commands)
from discord.abc import GuildChannel
from discord.ext import commands
from discord.ui import Button, Select, View

from ..music import (YTDL, APIResult, BasePlaylist, BaseTrack,
                     DifferentVoiceChannelException, MusicException,
                     NoVoiceChannelException, Payload, Queue)
from ..protocols import GuildMessageable

if TYPE_CHECKING:
    from ..bot import Bot


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
        self._selected_values = [str(idx)]
        self.options[idx].default = True
        self.options[self.page].default = False
        self.page = idx
        if self.view is not None:
            embed, file = await track.create_thumbnail(self.view.payload.bot.session)
            await interaction.response.edit_message(embed=embed.set_footer(text=f"{track.title}\nby {track.uploader}"), attachments=[file])

class PlayView(View):
    def __init__(
        self,
        payload: Payload,
        queue: Queue,
        *items: Union[BaseTrack, BasePlaylist],
    ):
        self.payload = payload
        self.queue = queue
        self.select = TrackSelect(*items)
        enqueue: Button["PlayView"] = Button(
            style=ButtonStyle.primary, label="Add to Queue"
        )
        enqueue.callback = self.enqueue
        self.add_item(self.select)
        self.add_item(enqueue)

    @classmethod
    async def display(cls, payload: Payload, queue: Queue, query: str):
        items = await YTDL.from_query(
            query, session=payload.bot.session, api_key=payload.bot.conf.env["YOUTUBE"]
        )
        head = items[0]
        embed, file = await head.create_thumbnail(payload.bot.session)
        embed.set_footer(text=f"{head.title}\nby {head.uploader}\n{len(head.entries) if isinstance(head, BasePlaylist) else ''}")
        await payload.interaction.followup.send(
            embed=embed, file=file, ephemeral=True, view=cls(payload, queue, *items)
        )
    
    async def enqueue(self, interaction: Interaction):
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
        await iact.response.defer(ephemeral=True)
        payload = await Payload.from_interaction(self.bot, iact)
        queue = self.get_queue(payload)
        await PlayView.display(payload, queue, query)


async def setup(bot: Bot):
    await bot.add_cog(Music(bot))
