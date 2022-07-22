from logging import getLogger
from typing import Any, Dict, Optional, Union, cast

from discord import (
    ButtonStyle,
    Embed,
    Guild,
    Interaction,
    Member,
    SelectOption,
    app_commands,
)
from discord.ext import commands
from discord.ui import Button, Select, View
from discord.utils import MISSING
from dataclasses import dataclass
from hk.music.errors import NoVoiceException

from ..bot import Bot
from ..music import (
    YTDL,
    BasePlaylist,
    BaseTrack,
    DifferentVoiceException,
    GuildOnlyException,
    Queue,
    Voice,
)
from ..protocols import GuildMessageable
from ..views import Paginator, Unit

logger = getLogger("discord")


@dataclass
class Payload:
    """Holds data required for most music functions"""

    bot: Bot
    guild: Guild
    voice_client: Voice
    user: Member
    channel: GuildMessageable
    interaction: Interaction

    @classmethod
    async def validate(cls, bot: Bot, iact: Interaction):
        if iact.guild is None:
            raise GuildOnlyException
        user = cast(Member, iact.user)
        voice_client = cast(Optional[Voice], iact.guild.voice_client)
        if (voice := user.voice) and (channel := voice.channel):
            if not voice_client:
                voice_client = await channel.connect(cls=Voice)
            elif channel != voice_client.channel:
                if len(voice_client.channel.members) == 1:
                    await voice_client.move_to(channel)
                else:
                    raise DifferentVoiceException
        else:
            raise NoVoiceException

        return cls(
            bot=bot,
            guild=iact.guild,
            voice_client=voice_client,
            user=user,
            channel=cast(GuildMessageable, iact.channel),
            interaction=iact,
        )


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


class TrackSelect(Select["PlayView"]):
    def __init__(self, *items: Union[BaseTrack, BasePlaylist]):
        self.items = items
        self.page = 0
        options = [
            SelectOption(label=t.title, value=str(i), description=f"By {t.uploader}")
            for i, t in enumerate(items)
        ]
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
            await interaction.response.edit_message(
                embed=banner.embed.set_footer(
                    text=f"{track.title}\nby {track.uploader}"
                ),
                attachments=[banner.file()],
                view=self.view,
            )


class PlayView(BaseMusicView):
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
        text = f"{head.title}\nby {head.uploader}"
        if isinstance(head, BasePlaylist):
            text += f"\n{len(head.entries)} tracks"
        await payload.interaction.followup.send(
            embed=banner.embed.set_footer(text=text),
            file=banner.file(),
            ephemeral=True,
            view=cls(payload, queue, *items),
        )

    async def enqueue(self, interaction: Interaction):
        track = self.select.items[int(self.select.values[0])]
        if message := interaction.message:
            if (
                self.queue.empty()
                and not self.queue.voice.is_playing()
                and isinstance(track, BaseTrack)
            ):
                await message.delete()  # avoid repeated "Queued" embeds for first-time singleton tracks
            else:
                embed = interaction.message.embeds[0]
                embed.set_footer(text="Queued\n" + str(embed.footer.text))
                await interaction.response.edit_message(
                    view=None, embed=embed, attachments=message.attachments
                )
        await self.queue.put(track)


class QueueView(Paginator):
    @classmethod
    async def display(cls, payload: Payload, queue: Queue):
        tracks = list(queue.deque)
        bot = payload.bot
        if np := queue.voice.track:
            banner = await np.create_banner(bot.session)
            embed = banner.embed.set_footer(
                text=f"{queue.progress}\n{queue.qsize()} tracks left"
            )
            start = Unit(embed=embed, files=[banner.file()])
        else:
            start = Unit(
                embed=Embed(description="The queue is empty :(", color=bot.conf.color)
            )
        items = [start]
        for i in range(0, len(tracks), 10):
            content = "\n".join(
                f"{i+x}. {t.title}" for x, t in enumerate(tracks[i : i + 10])
            )
            embed = Embed(description=f"```md\n{content}\n```", color=bot.conf.color)
            items.append(Unit(embed=embed))
        view = cls(payload.bot, *items)
        await payload.interaction.response.send_message(
            embed=start.embed or MISSING, files=start.files, view=view, ephemeral=True
        )


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
        payload = await Payload.validate(self.bot, iact)
        queue = self.get_queue(payload)
        await PlayView.display(payload, queue, query)

    @app_commands.command()
    async def pause(self, iact: Interaction):
        """Pause the current track"""
        payload = await Payload.validate(self.bot, iact)
        queue = self.get_queue(payload)
        queue.voice.pause()
        await iact.response.send_message(
            embed=Embed(description="Paused!", color=self.bot.conf.color)
        )

    @app_commands.command()
    async def resume(self, iact: Interaction):
        """Resume the current track"""
        payload = await Payload.validate(self.bot, iact)
        queue = self.get_queue(payload)
        queue.voice.resume()
        await iact.response.send_message(
            embed=Embed(description="Resumed!", color=self.bot.conf.color)
        )

    @app_commands.command()
    @app_commands.describe(to="The index to skip to")
    async def skip(self, iact: Interaction, to: int = 0):
        """Skip the current track"""
        payload = await Payload.validate(self.bot, iact)
        queue = self.get_queue(payload)
        if to > queue.qsize():
            embed = Embed(
                description=f"There are only {queue.qsize()} tracks in the queue!"
                if not queue.empty()
                else "The queue is empty!",
                color=self.bot.conf.color,
            )
        elif np := queue.voice.track:
            banner = await np.create_banner(self.bot.session)
            embed = banner.embed
            embed.description = "Skipping"
            skipped = [queue.deque.popleft() for _ in range(to)]
            text = np.title
            if skipped:
                text += f"\n(and {len(skipped)} tracks)"
            embed.set_footer(text=text, icon_url=np.get_thumbnail())
            payload.voice_client.stop()
        else:
            embed = Embed(description="Nothing to skip :(", color=self.bot.conf.color)
        await iact.response.send_message(embed=embed)

    @app_commands.command()
    async def queue(self, iact: Interaction):
        """See the current and upcoming tracks"""
        payload = await Payload.validate(self.bot, iact)
        await QueueView.display(payload, self.get_queue(payload))

    @app_commands.command()
    async def nowplaying(self, iact: Interaction):
        """See the currently playing track and it's progress"""
        payload = await Payload.validate(self.bot, iact)
        queue = self.get_queue(payload)
        if track := queue.voice.track:
            banner = await track.create_banner(self.bot.session)
            await iact.response.send_message(
                embed=banner.embed.set_footer(text=queue.progress),
                file=banner.file(),
            )
            queue.add_updater(await iact.original_message())
        else:
            await iact.response.send_message(
                embed=Embed(
                    description="Nothing is playing :(", color=self.bot.conf.color
                )
            )

    @app_commands.command()
    async def volume(self, iact: Interaction, volume: Optional[float]):
        """See or set the playback volume"""
        payload = await Payload.validate(self.bot, iact)
        queue = self.get_queue(payload)
        if volume:
            queue.voice.volume = volume

        await iact.response.send_message(
            embed=Embed(
                description=f"Volume: {queue.voice.volume}", color=self.bot.conf.color
            )
        )

    @app_commands.command()
    async def loop(self, iact: Interaction):
        """Toggles track looping for the guild's queue"""
        payload = await Payload.validate(self.bot, iact)
        queue = self.get_queue(payload)
        text = f"Looping is now {'on' if queue.repeat() else 'off'}!"
        await iact.response.send_message(
            embed=Embed(description=text, color=self.bot.conf.color)
        )

    @app_commands.command()
    async def banner(self, iact: Interaction, query: str):
        """Creates a banner for a track or playlist"""
        await iact.response.defer()
        session = self.bot.session
        res = await YTDL.from_query(
            query, session=session, api_key=self.bot.conf.env["YOUTUBE"]
        )
        item = res[0]
        banner = await item.create_banner(session=session)
        await iact.followup.send(embed=banner.embed, file=banner.file())


async def setup(bot: Bot):
    await bot.add_cog(Music(bot))
