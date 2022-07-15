from __future__ import annotations

import asyncio
from collections import deque
from typing import Any, Optional, Union, cast

from ..bot import Bot
from ..protocols import GuildMessageable
from .audio import Audio, Voice
from .errors import NoVoiceException, UnknownTrackException
from .track import BasePlaylist, BaseTrack
from .ytdl import YTDL


class Queue(asyncio.Queue[BaseTrack]):
    def __init__(self, bot: Bot, *, bound: GuildMessageable):
        super().__init__()
        self.deque: deque[BaseTrack] = self._queue  # type: ignore
        self.guild = bound.guild
        self.bound = bound
        self.loop = asyncio.get_running_loop()
        self.bot = bot

    async def next(self) -> Any:
        try:
            partial = await self.get()
            track = await YTDL.to_track(partial)
        except UnknownTrackException:
            return self._next()
        await self.voice.play(track, after=self._next)

        banner = await track.create_banner(self.bot.session)
        await self.bound.send(
            embed=banner.embed.set_footer(text=self.progress), file=banner.file()
        )

    def _next(self, exception: Optional[Exception] = None):
        self.loop.create_task(self.next())

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

    @property
    def progress(self):
        """Returns a string representing the Queue's current state"""
        if (track := self.voice.track) and (src := self.source):
            pct = int(src.seconds() * 100 // track.duration)
            progress = f"{src.seconds()/60:.2f}/{track.runtime} | {pct}%"
            if self.voice.is_paused():
                progress += "\nPaused"
            return f"Now Playing\n{track.title}\n{progress}"
        else:
            return f"The Queue is empty :("
