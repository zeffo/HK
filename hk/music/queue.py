from __future__ import annotations

from discord import VoiceClient

from . import BaseTrack, BasePlaylist, YTDL, Audio, Track
from discord.abc import GuildChannel
import asyncio
from typing import Union, Optional


class Lock(asyncio.Lock):
    track: Optional[Track] = None

    async def bind(self, track: Track):
        self.track = track
        await super().acquire()

    def release(self) -> None:
        self.track = None
        super().release()


class Queue(asyncio.Queue["BaseTrack"]):
    def __init__(self, *, bound: GuildChannel):
        super().__init__(500)
        self.bound = bound
        self.guild = bound.guild
        self.looping: bool = False
        self.lock = Lock()
        self.loop = asyncio.get_running_loop()

    async def play(self, track: Track):
        source = Audio(track.url)
        await self.lock.bind(track)
        if (
            self.guild
            and (vc := self.guild.voice_client)
            and isinstance(vc, VoiceClient)
        ):
            vc.play(source, after=self._handle_next)

    def _handle_next(self, exception: Optional[Exception] = None):
        self.loop.create_task(self.next())

    async def next(self):
        if self.lock.locked():
            self.lock.release()
        partial = await self.get()
        track = await YTDL.to_track(partial)
        await self.play(track)

    async def put(self, item: Union[BaseTrack, BasePlaylist]):
        size = self.qsize()
        if isinstance(item, BasePlaylist):
            for track in item.entries:
                await super().put(track)
        else:
            await super().put(item)
        if size == 0 and not self.lock.locked():
            await self.next()

    async def get(self):
        item = await super().get()
        if self.looping:
            await self.put(item)
        return item
