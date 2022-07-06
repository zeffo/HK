import asyncio
from collections import deque
from typing import Optional, Union

from discord import VoiceClient

from ..bot import Bot
from ..protocols import GuildMessageable
from .audio import Audio
from .errors import MusicException, NoVoiceChannelException
from .track import BasePlaylist, BaseTrack, Track
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
    _queue: deque[BaseTrack]

    def __init__(self, bot: Bot, *, bound: GuildMessageable):
        super().__init__(500)
        self.bot = bot
        self.bound = bound
        self.guild = bound.guild
        self.lock = Lock()
        self.loop = asyncio.get_running_loop()
        self.queue = self._queue

    @property
    def voice_client(self):
        if isinstance(self.guild.voice_client, VoiceClient):
            return self.guild.voice_client
        raise NoVoiceChannelException

    async def play(self):
        partial = await self.get()
        try:
            track = await YTDL.to_track(partial)
        except MusicException as e:
            self.next(e)
        else:
            await self.lock.hold(track)
            source = Audio(track.url)
            self.voice_client.play(source, after=self.next)
            banner = await track.create_banner(self.bot.session)
            embed = banner.embed()
            embed.set_footer(text=f"Now Playing\n{track.title}\n{track.runtime}")
            await self.bound.send(embed=embed, file=banner.file())

    def next(self, exception: Optional[Exception]):
        self.lock.release()
        self.loop.create_task(self.play())

    async def put(self, item: Union[BaseTrack, BasePlaylist]):
        size = self.qsize()
        if isinstance(item, BasePlaylist):
            for track in item.entries:
                await super().put(track)
        else:
            await super().put(item)

        if size == 0 and not self.lock.locked():
            await self.play()
