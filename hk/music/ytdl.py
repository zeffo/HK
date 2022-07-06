import asyncio
from logging import getLogger
from re import compile
from typing import Any, Dict, Union

from aiohttp import ClientSession
from yt_dlp import YoutubeDL

from .errors import MusicException, UnknownTrackException
from .track import APIItem, APIResult, BasePlaylist, BaseTrack, Track

__all__ = ("YTDL",)

SEARCH = "https://www.googleapis.com/youtube/v3/search?part=snippet&maxResults=10&q={0}&type=video&key={1}"
VIDEO = compile(
    r"^(?:https?:\/\/)?(?:www\.)?(?:youtu\.be\/|youtube\.com\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=))((\w|-){11})(?:\S+)?$"
)
PLAYLIST = compile(r"^.*(youtu.be\/|list=)([^#\&\?]*).*")


class YTDL(YoutubeDL):
    def __init__(self):
        params: Dict[str, Any] = {
            "format": "bestaudio",
            "outtmpl": "%(extractor)s-%(id)s-%(title)s.%(ext)s",
            "restrictfilenames": True,
            "noplaylist": False,
            "nocheckcertificate": True,
            "ignoreerrors": True,
            "logtostderr": False,
            "quiet": True,
            "no_warnings": True,
            "default_search": "auto",
            "source_address": "0.0.0.0",
            "extract_flat": True,
            "skip_download": True,
            "logger": getLogger("discord"),
        }
        super().__init__(params=params)

    @classmethod
    async def get_data(cls, uri: str) -> Dict[Any, Any]:
        """Extracts video data from YouTube from the given URI"""

        def to_thread() -> Dict[Any, Any]:
            with cls() as yd:
                data: Dict[Any, Any] = yd.extract_info(uri, download=False)
            return data

        return await asyncio.to_thread(to_thread)

    @classmethod
    async def from_api(cls, query: str, *, session: ClientSession, api_key: str):
        async with session.get(SEARCH.format(query, api_key)) as resp:
            json = await resp.json()
            if not json.get("items"):
                raise UnknownTrackException
            return APIResult(**json)

    @classmethod
    async def to_track(cls, partial: Union[BaseTrack, APIItem]):
        if not isinstance(partial, Track):
            data = await cls.get_data(str(partial.id))
            if data is None:
                raise MusicException("Couldn't download that track!")
            return Track(**data)
        return partial

    @classmethod
    async def from_query(cls, query: str, *, session: ClientSession, api_key: str):
        if match := VIDEO.match(query):
            data = await cls.get_data(match.group(1))
            return (Track(**data),)
        elif PLAYLIST.match(query):
            data = await cls.get_data(query)
            return (BasePlaylist(**data),)
        else:
            return tuple(
                (await cls.from_api(query, session=session, api_key=api_key)).partials()
            )
