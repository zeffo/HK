from __future__ import annotations

import asyncio
from typing import Any, Optional, Union

from discord import Embed, Message, VoiceClient
from discord.abc import GuildChannel, Messageable

from ..bot import Bot
from .audio import Audio
from .track import BasePlaylist, BaseTrack, Track
from .ytdl import YTDL

__all__ = ("Queue",)


class Lock(asyncio.Lock):
    """Lock that"""

    track: Optional[Track] = None

    async def bind(self, track: Track):
        self.track = track
        await super().acquire()

    def release(self) -> None:
        self.track = None
        super().release()


class Slider:
    cursor = "🔘"
    segment = "➖"

    def __init__(self):
        self.position = 0
        self.slider = list(self.cursor + self.segment * 9)

    def render(self, complete: float, total: float):
        pct = round((complete * 100) / total)
        idx = round(pct, -1) // 10 - 1
        idx = max(idx, 0)
        self.slider[self.position] = self.segment
        self.slider[idx] = self.cursor
        self.position = idx
        return "".join(self.slider)


class DurationEditTask(asyncio.Task[Any]):
    def __init__(self, source: Audio, track: Track, message: Message):
        self.source = source
        self.track = track
        self.message = message
        self.slider = Slider()
        self.embed = message.embeds[0]
        parts = (self.embed.footer.text or "").split("\n")
        self.embed.set_footer(text="\n".join(parts[:-1]))
        super().__init__(self.edit_duration())

    async def edit(self, embed: Embed):
        try:
            await self.message.edit(embed=embed, attachments=[])
        except Exception:
            self.cancel()

    async def edit_duration(self):
        chunk = self.track.duration / 10
        while True:
            await asyncio.sleep(chunk)
            render = self.slider.render(self.source.seconds(), self.track.duration)
            rendered = f"{self.embed.footer.text}\n{render}"
            embed = self.embed.copy().set_footer(text=rendered)
            await self.edit(embed=embed)

    async def stop(self):
        footer = f"{self.embed.footer.text}\n{self.slider.render(10,10)}"
        await self.message.edit(embed=self.embed.set_footer(text=footer))
        self.cancel()


class Queue(asyncio.Queue["BaseTrack"]):
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
            vc.play(source, after=self._handle_next)
        if isinstance(self.bound, Messageable):
            embed, file = await track.create_thumbnail(self.bot.session)
            message = await self.bound.send(
                embed=embed.set_footer(
                    text=f"Now Playing\n{track.title}\nDuration: {track.runtime}\n{''.join(Slider().slider)}"
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
