from __future__ import annotations
from typing import Optional, List, Union
from .constants import VIDEO, PLAYLIST, SEARCH
from .ytdl import YTDL
from pydantic import BaseModel
import aiohttp


class Track(BaseModel):
    """Represents a YouTube video"""
    id: str
    title: str
    uploader: str
    duration: Union[int, float]
    url: str

    stream: Optional[str] = None
    thumbnail: Optional[str] = None

    async def update(self) -> None:
        if not self.stream:
            data = await YTDL(fast=False).get_data(self.id)
            super().__init__(**data)

    @classmethod
    async def from_api(cls, query: str, *, session: Optional[aiohttp.ClientSession]=None, token: str) -> Track:
        session = session or aiohttp.ClientSession()
        async with session.get(SEARCH.format(query, token)) as resp:
            json = await resp.json()
        ytdl = YTDL()
        data = await ytdl.get_data(json["items"][0]["id"]["videoId"])
        return cls(**data)

    @classmethod
    async def from_query(cls, query: str, *, session: Optional[aiohttp.ClientSession]=None, fast: bool=True, token: str) -> List[Track]:
        """Parses the given query and returns the associated tracks"""
        ytdl = YTDL(fast=fast)
        tracks: List[Track] = []
        if match := VIDEO.match(query):
            data = await ytdl.get_data(match.groups()[0])
            tracks.append(cls(**data))
        elif PLAYLIST.match(query):
            data = await ytdl.get_data(query)
            if fast:
                for track in data['entries']:
                    track['thumbnail'] = track['thumbnails'][-1]['url']
                    tracks.append(cls(**track))
            else:
                for track in data['entries']:
                    track['stream'] = track['url']
                    track['url'] = track['webpage_url']
                    tracks.append(cls(**track))
        else:
            tracks.append(await cls.from_api(query, session=session, token=token))
        return tracks

    def __repr__(self):
        return f""" {self.title} by {self.uploader} | Duration: {self.duration} | URL: {self.url} """

    