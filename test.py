# type: ignore
from yt_dlp import YoutubeDL   # type: ignore
from re import compile 
from typing import Dict, Any, List, Optional
from asyncio import get_running_loop

SEARCH = "https://www.googleapis.com/youtube/v3/search?part=snippet&maxResults=1&q={0}&type=video&key={1}"
VIDEO = compile(r"^(?:https?:\/\/)?(?:www\.)?(?:youtu\.be\/|youtube\.com\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=))((\w|-){11})(?:\S+)?$")
PLAYLIST = compile(r"^.*(youtu.be\/|list=)([^#\&\?]*).*")

class YTDLParams:
    params: Dict[str, Any] = {
        "format": "best/bestaudio",
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
    }

    @property
    def full(self) -> Dict[str, Any]:
        """Returns parameters to retrieve full information from YoutubeDL"""
        return self.params

    @property
    def fast(self) -> Dict[str, Any]:
        """Returns parameters to retrieve partial information from YoutubeDL"""
        skip = {"extract_flat": True, "skip_download": True}
        skip.update(self.params)
        return skip


class YTDL(YoutubeDL):

    def __init__(self, fast: bool=True):
        params = YTDLParams()
        p = params.fast if fast else params.full
        print(p)
        super().__init__(p)
    
    async def get_data(self, uri: str) -> Dict[Any, Any]:
        """Extracts video data from YouTube from the given URI"""
        def to_thread() -> Dict[Any, Any]:
            with self as yd:
                data: Dict[Any, Any] = yd.extract_info(uri, download=False)
            return data
        return await get_running_loop().run_in_executor(None, to_thread)

url = "https://www.youtube.com/playlist?list=PL718kqv5yMiK7SmaLo368oF4oSQMaL52J"

with YTDL() as yd:
    d = yd.extract_info(url, download=False)['entries']
    print(d[0])

with YTDL(fast=False) as yd:
    d = yd.extract_info(url, download=False)['entries']
    print(d[0])