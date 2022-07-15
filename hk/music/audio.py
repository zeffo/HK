from asyncio import Event, Lock
from io import BufferedIOBase
from typing import Any, Callable, Dict, Optional, Union, cast

from discord import AudioSource, FFmpegPCMAudio, PCMVolumeTransformer, VoiceClient

from .track import Track

FFMPEG_OPTS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}


class Audio(PCMVolumeTransformer[AudioSource]):
    """AudioSource to keep track of amount of data read (in ms)"""

    def __init__(
        self,
        stream: Union[str, BufferedIOBase],
        volume: float = 0.5,
        *,
        opts: Dict[str, str] = FFMPEG_OPTS
    ):
        source = FFmpegPCMAudio(stream, **opts)
        super().__init__(source, volume)
        self.done = 0

    def read(self):
        self.done += 20
        return super().read()

    def seconds(self):
        return round(self.done / 1000, 2)


class Voice(VoiceClient):
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.lock = Lock()
        self.resumed = Event()
        self.track: Optional[Track] = None
        self._volume: float = 0.5

    def _wrap_next(self, fn: Callable[..., Any]):
        def inner(ex: Optional[Exception] = None):
            self.lock.release()
            self.resumed.clear()
            fn(ex)

        return inner

    async def play(self, track: Track, *, after: Callable[[Optional[Exception]], Any]):  # type: ignore
        await self.lock.acquire()
        self.track = track
        src = Audio(track.url, volume=self._volume)
        super().play(src, after=self._wrap_next(after))
        self.resumed.set()

    def pause(self) -> None:
        self.resumed.clear()
        return super().pause()

    def resume(self) -> None:
        self.resumed.set()
        return super().resume()

    @property
    def volume(self):
        return self._volume

    @volume.setter
    def volume(self, vol: float):
        self._volume = vol
        if self.source:
            src = cast(Audio, self.source)
            src.volume = vol
