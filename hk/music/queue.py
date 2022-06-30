from __future__ import annotations

import asyncio
from logging import getLogger
from typing import Any, Optional, Union

from discord import Embed, Message, VoiceClient
from discord.abc import GuildChannel, Messageable

from ..bot import Bot
from .audio import Audio
from .track import BasePlaylist, BaseTrack, Track
from .ytdl import YTDL

__all__ = ("Queue",)

logger = getLogger("discord")


class Lock(asyncio.Lock):
    """Lock that can hold a Track"""

    track: Optional[Track] = None

    async def bind(self, track: Track):
        self.track = track
        await super().acquire()

    def release(self) -> None:
        self.track = None
        super().release()


class DurationEditTask(asyncio.Task[Any]):
    """A Task to update the track completion status on a Message every 10 seconds"""

    def __init__(self, source: Audio, track: Track, message: Message):
        self.source = source
        self.track = track
        self.message = message
        self.embed = message.embeds[0]
        super().__init__(self.edit_duration())

    async def edit(self, embed: Embed):
        try:
            await self.message.edit(embed=embed, attachments=self.message.attachments)
        except Exception:
            self.cancel()

    async def edit_duration(self):
        while True:
            await asyncio.sleep(10)
            pct = (self.source.seconds() / self.track.duration) * 100
            rendered = f"{self.embed.footer.text} ({pct:.2f}%)"
            embed = self.embed.copy().set_footer(text=rendered)
            await self.edit(embed=embed)

    async def stop(self):
        self.cancel()
        await self.message.delete()


class Queue(asyncio.Queue["BaseTrack"]):
    """Handles automatic playback, playlist parsing and more"""

    def __init__(self, bot: Bot, *, bound: GuildChannel):
        super().__init__(500)
        self.bot = bot
        self.bound = bound
        self.guild = bound.guild
        self.looping: bool = False
        self.lock = Lock()
        self.loop = asyncio.get_running_loop()
        self.task: Optional[DurationEditTask] = None

    def get_source(self):
        if vc := self.guild.voice_client:
            if isinstance(vc, VoiceClient) and isinstance(vc.source, Audio):
                return vc.source

    def set_task(self, track: Track, message: Message):
        if source := self.get_source():
            self.task = DurationEditTask(source, track, message)

    async def play(self, track: Track):
        source = Audio(track.url)
        await self.lock.bind(track)
        if (
            self.guild
            and (vc := self.guild.voice_client)
            and isinstance(vc, VoiceClient)
        ):
            if vc.is_playing():
                vc.stop()
            vc.play(source, after=self._handle_next)
        if isinstance(self.bound, Messageable):
            embed, file = await track.create_thumbnail(self.bot.session)
            message = await self.bound.send(
                embed=embed.set_footer(
                    text=f"Now Playing\n{track.title}\nDuration: {track.runtime}"
                ),
                file=file,
            )
            self.set_task(track, message)

    def _handle_next(self, exception: Optional[Exception] = None):
        self.loop.create_task(self.next())

    async def next(self):
        if self.lock.locked():
            self.lock.release()
        if self.task:
            await self.task.stop()
            self.task = None
        partial = await self.get()
        track = await YTDL.to_track(partial)
        if track:
            await self.play(track)
        else:
            await self.next()

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

    def skip(self):
        if vc := self.guild.voice_client:
            if isinstance(vc, VoiceClient):
                vc.stop()
