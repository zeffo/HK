from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Union

from discord import (ButtonStyle, Embed, Guild, Interaction, Member,
                     SelectOption, VoiceClient, app_commands)
from discord.abc import GuildChannel
from discord.ext import commands
from discord.ui import Button, Select, View

from ..music import (YTDL, APIResult, BasePlaylist, BaseTrack,
                     DifferentVoiceChannelException, GuildOnlyException,
                     NoVoiceChannelException, Queue)

if TYPE_CHECKING:
    from ..bot import Bot


async def check(interaction: Interaction):
    """
    Checks the following:
        - Interaction takes place in a Guild
        - The user is in the same voice channel as the bot
    """
    if not isinstance(interaction.user, Member) or interaction.guild is None:
        raise GuildOnlyException
    voice = interaction.user.voice
    client = interaction.guild.voice_client
    if voice and voice.channel:
        if not client:
            client = await voice.channel.connect()
        elif (
            isinstance(client, VoiceClient)
            and client.channel != voice.channel
            and len(client.channel.members) == 1
        ):
            await client.move_to(voice.channel)
        elif client.channel != voice.channel:
            raise DifferentVoiceChannelException
    else:
        raise NoVoiceChannelException
    return True


class BaseMusicView(View):
    async def interaction_check(self, interaction: Interaction) -> bool:
        return await check(interaction)


def requires_voice_channel():
    """Decorator for app commands that uses the base check"""
    return app_commands.check(check)


class TrackSelect(Select["PlayView"]):
    def __init__(self, *items: Union[BaseTrack, BasePlaylist]):
        self.page = 0
        self.items = items
        options = [
            SelectOption(
                label=item.title[:100], description=f"By {item.uploader}", value=str(i)
            )
            for i, item in enumerate(items)
        ]
        options[0].default = True
        super().__init__(options=options)
        self._selected_values = ["0"]

    async def callback(self, interaction: Interaction):
        assert self.view is not None
        idx = int(self.values[0])
        item = self.items[idx]
        self.options[idx].default = True
        self.options[self.page].default = False
        self.page = idx
        self._selected_values = [str(idx)]
        embed, file = await item.create_thumbnail(self.view.bot.session)
        await interaction.response.edit_message(
            attachments=[file],
            view=self.view,
            embed=embed.set_footer(text=f"{item.title}\nby {item.uploader}"),
        )

    def selected(self):
        return self.items[int(self.values[0])]


class CancelButton(Button["View"]):
    def __init__(self):
        super().__init__(style=ButtonStyle.danger, label="Cancel")

    async def callback(self, interaction: Interaction):
        if m := interaction.message:
            await m.delete()


class PlayView(BaseMusicView):
    def __init__(self, bot: Bot, queue: Queue, *items: Union[BaseTrack, BasePlaylist]):
        super().__init__()
        self.bot = bot
        self.queue = queue
        self.items = items
        self.menu = TrackSelect(*items)
        enqueue: Button["PlayView"] = Button(
            style=ButtonStyle.primary, label="Add to Queue"
        )
        enqueue.callback = self.enqueue
        self.add_item(self.menu)
        self.add_item(enqueue)

    async def enqueue(self, interaction: Interaction):
        await interaction.response.edit_message(content="Added to queue!", view=None)
        track = self.menu.selected()
        await self.queue.put(track)

    @classmethod
    async def create(cls, bot: Bot, iact: Interaction, queue: Queue, query: str):
        await iact.response.defer(ephemeral=True)
        result = await YTDL.from_query(
            query, session=bot.session, api_key=bot.conf.env["YOUTUBE"]
        )
        items = result.partials() if isinstance(result, APIResult) else [result]
        view = cls(bot, queue, *items)
        track = items[0]
        embed, file = await track.create_thumbnail(bot.session)
        text = f"{track.title}\nby {track.uploader}"
        if isinstance(track, BasePlaylist):
            text += f"\n{len(track.entries)} tracks"
        embed.set_footer(text=text)
        await iact.followup.send(embed=embed, file=file, view=view, ephemeral=True)


class Music(commands.Cog):
    def __init__(self, bot: "Bot"):
        self.bot = bot
        self.queues: Dict[Guild, Queue] = {}

    def get_queue(self, channel: GuildChannel):
        return self.queues.setdefault(channel.guild, Queue(bound=channel, bot=self.bot))

    @app_commands.command()
    @requires_voice_channel()
    async def play(self, interaction: Interaction, query: str):
        if isinstance(interaction.channel, GuildChannel):
            return await PlayView.create(
                self.bot, interaction, self.get_queue(interaction.channel), query
            )
        raise GuildOnlyException

    @app_commands.command()
    @requires_voice_channel()
    async def skip(self, interaction: Interaction):
        assert (
            isinstance(interaction.channel, GuildChannel)
            and interaction.guild is not None
        )
        queue = self.get_queue(interaction.channel)
        track = queue.lock.track
        if track:
            embed, _ = await track.create_thumbnail(self.bot.session)
            embed.set_author(
                name="Skipping", icon_url=interaction.user.display_avatar.url
            ).set_footer(
                text=f"{track.title}\nby {track.uploader}",
                icon_url=track.get_thumbnail(),
            )
        else:
            embed = Embed(description="Nothing to skip!", color=self.bot.conf.color)
        await interaction.response.send_message(embed=embed)
        queue.skip()


async def setup(bot: "Bot"):
    await bot.add_cog(Music(bot))
