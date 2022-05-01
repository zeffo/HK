from asyncio import get_running_loop
from yt_dlp import YoutubeDL   # type: ignore
from .constants import YTDLParams
from typing import Dict, Any


class YTDL(YoutubeDL):

    def __init__(self, fast: bool=True):
        params = YTDLParams().fast if fast else YTDLParams().full
        super().__init__(params)
    
    async def get_data(self, uri: str) -> Dict[Any, Any]:
        """Extracts video data from YouTube from the given URI"""
        def to_thread() -> Dict[Any, Any]:
            with self as yd:
                data: Dict[Any, Any] = yd.extract_info(uri, download=False)
            return data
        return await get_running_loop().run_in_executor(None, to_thread)
        

