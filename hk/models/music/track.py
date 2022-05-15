from __future__ import annotations

from html import unescape
from typing import Any, Dict, List, Optional, Union

import aiohttp
from discord import Embed
from pydantic import BaseModel

from .constants import PLAYLIST, SEARCH, VIDEO
from .ytdl import YTDL


class BaseTrack:
    def __init__(self, id: str, title: str, uploader: str, thumbnail: str):
        self.id = id
        self.title = title
        self.uploader = uploader
        self.thumbnail = thumbnail

    def embed(self):
        e = Embed(title=self.title, description=f"Uploaded by **{self.uploader}**")
        e.set_image(url=self.thumbnail)
        return e


class PartialTrack(BaseModel, BaseTrack):
    """Represents a partially fetched YouTube Video"""
    id: str
    title: str
    uploader: str
    duration: Union[int, float]
    url: str
    thumbnails: List[Dict[str, str]]

    @property
    def thumbnail(self) -> str:
        return self.thumbnails[-1]['url']

    def __repr__(self):
        return f"PartialTrack({self.title}, {self.url})"

class APITrack(BaseTrack):
    """Represents a YouTube video from the YouTube Data API"""

    __slots__ = ('id', 'title', 'thumbnail', 'uploader')

    def __init__(self, data: Dict[Any, Any]):
        self.id: str = data["id"]["videoId"]
        snip = data["snippet"]
        self.title: str = snip["title"]
        self.thumbnail: str = snip["thumbnails"]["high"]["url"]
        self.uploader: str = snip["channelTitle"]

        for attr in self.__slots__:
            setattr(self, attr, unescape(getattr(self, attr)))

    def __repr__(self):
        return f"APITrack({self.title}, https://youtube.com/watch?v={self.id})"
    

class Track(BaseModel, BaseTrack):
    """Represents a YouTube video"""
    id: str
    title: str
    uploader: str
    duration: Union[int, float]
    webpage_url: str
    thumbnail: str
    url: str

    @staticmethod
    async def from_api(query: str, *, session: Optional[aiohttp.ClientSession]=None, token: str) -> List[APITrack]:
        session = session or aiohttp.ClientSession()
        async with session.get(SEARCH.format(query, token)) as resp:
            json = await resp.json()
        return [APITrack(track) for track in json["items"]]

    @staticmethod
    async def from_query(query: str, *, session: Optional[aiohttp.ClientSession] = None, fast: bool = True, token: str) -> Union[List[Union[PartialTrack, Track]], List[Track], List[APITrack]]:
        """Parses the given query and returns the associated tracks"""
        cls = Track
        ytdl = YTDL(fast=fast)
        if match := VIDEO.match(query):
            data = await ytdl.get_data(match.groups()[0])
            return [cls(**data)]
        elif PLAYLIST.match(query):
            data = await ytdl.get_data(query)
            if fast:
                cls = PartialTrack
            return [cls(**track) for track in data['entries']]
        else:
            return await cls.from_api(query, session=session, token=token)

    @classmethod
    async def from_partial(cls, partial: Union[Track, PartialTrack, APITrack]):
        if isinstance(partial, Track):
            return partial
        data = await YTDL(fast=False).get_data(partial.id)
        return cls(**data)

    def __repr__(self):
        return f"Track({self.title}, {self.webpage_url})"



ResultsType = Union[List[Union[PartialTrack, Track]], List[Track], List[APITrack]]
TrackType = Union[PartialTrack, APITrack, Track]
