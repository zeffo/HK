from __future__ import annotations

import asyncio
from collections import deque
from typing import Any, Optional, Set, Union

from discord import Message, NotFound, VoiceClient

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


class NowPlayingTask(asyncio.Task[Any]):
    def __init__(self, message: Message, queue: Queue, *, buffer: int = 10):
        self.queue = queue
        self.message = message
        self.track = queue.lock.track
        self.buffer = buffer
        queue.tasks.add(self)
        super().__init__(self.task())

    async def task(self):
        track = self.track
        while self.queue.lock.track == track:
            await asyncio.sleep(self.buffer)
            await self.queue.playing.wait()
            if track is not None:
                banner = await track.create_banner(self.queue.bot.session)
                embed = banner.embed().set_footer(
                    text=f"Now Playing\n{track.title}\n{self.queue.progress}"
                )
                try:
                    await self.message.edit(embed=embed, attachments=[banner.file()])
                except NotFound:
                    break
        await self.stop()

    async def stop(self):
        try:
            await self.message.delete()
        except NotFound:
            pass

        self.cancel()


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
        self.tasks: Set[NowPlayingTask] = set()
        self.playing = asyncio.Event()

    @property
    def voice_client(self):
        if isinstance(self.guild.voice_client, VoiceClient):
            return self.guild.voice_client
        raise NoVoiceChannelException

    @property
    def source(self):
        s = self.voice_client.source
        if isinstance(s, Audio):
            return s
        raise MusicException("Invalid AudioSource")

    def pause(self):
        self.playing.clear()
        self.voice_client.pause()

    def resume(self):
        self.playing.set()
        self.voice_client.resume()

    @property
    def progress(self) -> str:
        if track := self.lock.track:
            src = self.source.seconds()
            pct = round(src * 100 / track.duration, 2)
            ret = f"{src/60:.2f}/{track.runtime} | {pct}%"
            if self.voice_client.is_paused():
                ret += "\nPaused"
        else:
            ret = "No track is playing :("
        return ret

    async def play(self):
        partial = await self.get()
        try:
            track = await YTDL.to_track(partial)
        except MusicException as e:
            self.next(e)
        else:
            self.playing.set()
            asyncio.gather(*[task.stop() for task in self.tasks])
            await self.lock.hold(track)
            source = Audio(track.url)
            self.voice_client.play(source, after=self.next)
            banner = await track.create_banner(self.bot.session)
            embed = banner.embed()
            embed.set_footer(text=f"Now Playing\n{track.title}\n{track.runtime}")
            message = await self.bound.send(embed=embed, file=banner.file())
            NowPlayingTask(message, self)

    def next(self, exception: Optional[Exception]):
        self.playing.clear()
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
