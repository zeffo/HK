from io import BufferedIOBase
from typing import Dict, Union

from discord import AudioSource, FFmpegPCMAudio, PCMVolumeTransformer

FFMPEG_OPTS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}


class Audio(PCMVolumeTransformer[AudioSource]):
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
