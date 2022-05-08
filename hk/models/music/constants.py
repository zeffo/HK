from re import compile 
from typing import Dict, Any

SEARCH = "https://www.googleapis.com/youtube/v3/search?part=snippet&maxResults=10&q={0}&type=video&key={1}"
VIDEO = compile(r"^(?:https?:\/\/)?(?:www\.)?(?:youtu\.be\/|youtube\.com\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=))((\w|-){11})(?:\S+)?$")
PLAYLIST = compile(r"^.*(youtu.be\/|list=)([^#\&\?]*).*")
FFMPEG_OPTS = {"before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5","options": "-vn"}

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
