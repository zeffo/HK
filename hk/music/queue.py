from __future__ import annotations

import asyncio
from collections import deque
from typing import Any, List, Optional, Union, cast

from discord import Message

from ..bot import Bot
from ..protocols import GuildMessageable
from .audio import Audio, Voice
from .errors import NoVoiceException, UnknownTrackException
from .track import BasePlaylist, BaseTrack
from .ytdl import YTDL


class UpdaterTask:
    def __init__(self, message: Message, *, queue: Queue, buffer: int = 10):
        self.message = message
        self.buffer = buffer
        self.queue = queue
        self.task = asyncio.create_task(self.updater())

    async def updater(self) -> None:
        while True:
            await asyncio.sleep(self.buffer)
            await self.queue.voice.resumed.wait()  # only update when a track is playing
            embed = self.message.embeds[0]
            embed.set_footer(text=self.queue.progress)
            try:
                await self.message.edit(
                    embed=embed, attachments=self.message.attachments
                )
            except Exception:
                await self.stop()
                break

    async def stop(self):
        try:
            await self.message.delete()
        except Exception:
            pass
        finally:
            self.task.cancel()


class Queue(asyncio.Queue[BaseTrack]):
    def __init__(self, bot: Bot, *, bound: GuildMessageable):
        super().__init__()
        self.deque: deque[BaseTrack] = self._queue  # type: ignore
        self.guild = bound.guild
        self.bound = bound
        self.loop = asyncio.get_running_loop()
        self.bot = bot
        self.updater_tasks: List[UpdaterTask] = []
        self.repeating = False

    async def next(self) -> Any:
        self._cancel_tasks()
        try:
            partial = await self.get()
            track = await YTDL.to_track(partial)
        except UnknownTrackException:
            return self._next()
        await self.voice.play(track, after=self._next)

        banner = await track.create_banner(self.bot.session)
        message = await self.bound.send(
            embed=banner.embed.set_footer(text=self.progress), file=banner.file()
        )
        self.add_updater(message)

    def _next(self, exception: Optional[Exception] = None):
        self.loop.create_task(self.next())

    def _cancel_tasks(self):
        asyncio.gather(*[task.stop() for task in self.updater_tasks])

    def add_updater(self, message: Message):
        self.updater_tasks.append(UpdaterTask(message, queue=self))

    @property
    def voice(self):
        """Returns the VoiceClient of the current guild"""
        v = self.guild.voice_client
        if v is None:
            raise NoVoiceException
        return cast(Voice, v)

    @property
    def source(self):
        return cast(Optional[Audio], self.voice.source)

    async def put(self, item: Union[BaseTrack, BasePlaylist]):
        empty = self.empty()
        if isinstance(item, BasePlaylist):
            for track in item.entries:
                self.put_nowait(track)
        else:
            await super().put(item)
        if not self.voice.track and empty:
            await self.next()

    async def get(self):
        track = await super().get()
        if self.repeating:
            await self.put(track)
        return track

    @property
    def progress(self):
        """Returns a string representing the Queue's current state"""
        if (track := self.voice.track) and (src := self.source):
            pct = int(src.seconds() * 100 // track.duration)
            progress = f"{src.seconds()/60:.2f}/{track.runtime} | {pct}%"
            if self.voice.is_paused():
                progress += "\nPaused"
            if self.repeating:
                progress += "\nLooping"
            return f"Now Playing\n{track.title}\n{progress}"
        else:
            return f"The Queue is empty :("

    def repeat(self):
        self.repeating = not self.repeating
        if track := self.voice.track:
            self.put_nowait(track)
        return self.repeating
