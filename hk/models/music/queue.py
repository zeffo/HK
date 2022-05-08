from __future__ import annotations
import asyncio
from discord import Guild, VoiceClient, Embed
from discord.abc import Messageable
from .track import TrackType, Track
from .audio import Audio
from ..bot import Bot
from typing import Any, Optional
from asyncio import get_running_loop

class Lock(asyncio.Lock):
    track: Optional[TrackType] = None

    async def acquire(self, track: TrackType):
        self.track = track
        await super().acquire()

    def release(self) -> None:
        self.track = None
        return super().release()

class Queue(asyncio.Queue):  # type: ignore
    """Represents the track queue for a Guild"""

    def __init__(self, guild: Guild, bot: Bot, *args: Any, broadcast: Optional[Messageable]=None, **kwargs: Any):
        super().__init__(*args, **kwargs)

        self.guild = guild
        self.bot = bot
        self.lock = Lock()
        self.volume: float = 0.5
        self.repeat: bool = False
        self.broadcast_channel: Optional[Messageable] = broadcast

    async def get(self) -> TrackType:
        item: TrackType = await super().get()
        if self.repeat:
            await self.put(item)
        return item

    async def add(self, *tracks: TrackType):
        for track in tracks:
            await self.put(track)
        
        if self.broadcast_channel:
            embed = None
            if self.lock.locked() and len(tracks) == 1:
                track = tracks[0]
                embed = track.embed()
                embed.set_author(name="Queued")
            elif len(tracks) > 1:
                embed = Embed(title=f"Queued {len(tracks)} items!")
            await self.broadcast(embed)

        if self.qsize() == len(tracks) and not self.lock.locked():
            await self.play()

    async def play(self):
        if vc := self.guild.voice_client:
            partial = await self.get()
            track = await Track.from_partial(partial)
            await self.lock.acquire(track)
            if isinstance(vc, VoiceClient):
                vc.play(Audio(track.url, volume=self.volume), after=self._handle_next)

    def _handle_next(self, e: Optional[Exception]):
        loop = get_running_loop()
        loop.create_task(self.next())

    async def next(self):
        self.lock.release()
        await self.play()

    async def broadcast(self, embed: Optional[Embed]):
        if embed and self.broadcast_channel:
            embed.color = self.bot.conf.color
            await self.broadcast_channel.send(embed=embed)
