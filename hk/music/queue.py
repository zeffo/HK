import asyncio
from typing import Any, Optional, Protocol, Sequence, Union, overload

from discord import (AllowedMentions, Embed, File, Guild, GuildSticker,
                     Message, MessageReference, PartialMessage, StickerItem, VoiceClient)
from discord.abc import GuildChannel, Messageable
from discord.ui import View


from ..bot import Bot
from ..protocols import GuildMessageable
from .track import BasePlaylist, BaseTrack, Track
from .errors import NoVoiceChannelException
from .audio import Audio
from .ytdl import YTDL


class Lock(asyncio.Lock):
    track: Optional[Track] = None

    async def hold(self, track: Track):
        await self.acquire()
        self.track = track
    
    def release(self) -> None:
        self.track = None
        return super().release()


class Queue(asyncio.Queue[BaseTrack]):
    def __init__(self, bot: Bot, *, bound: GuildMessageable):
        super().__init__(500)
        self.bot = bot
        self.bound = bound
        self.guild = bound.guild
        self.lock = Lock()

    @property
    def voice_client(self):
        if isinstance(self.guild.voice_client, VoiceClient):
            return self.guild.voice_client
        raise NoVoiceChannelException

    async def play(self):
        partial = await self.get()
        track = await YTDL.to_track(partial)
        if track:
            await self.lock.hold(track)
            source = Audio(track.url)
            self.voice_client.play(source, after=self.next)
            embed, file = await track.create_thumbnail(self.bot.session)
            embed.set_footer(text=f"")

    def next(self, exception: Optional[Exception]):
        asyncio.create_task(self.play())

    async def put(self, item: Union[BaseTrack, BasePlaylist]):
        size = self.qsize()
        if isinstance(item, BasePlaylist):
            for track in item.entries:
                await super().put(track)
        else:
            await super().put(item)
        
        if size == 0 and not self.lock.locked():
            await self.play()