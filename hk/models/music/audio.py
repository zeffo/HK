from io import BufferedIOBase
from typing import Dict, Union

from discord import AudioSource, FFmpegPCMAudio, PCMVolumeTransformer

from .constants import FFMPEG_OPTS


class Audio(PCMVolumeTransformer[AudioSource]):
    def __init__(self, stream: Union[str, BufferedIOBase], volume: float=0.5, *, opts: Dict[str, str]=FFMPEG_OPTS):
        source = FFmpegPCMAudio(stream, **opts)
        super().__init__(source, volume)
        self.done = 0

    def read(self):
        self.done += 20
        return super().read()
