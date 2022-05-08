from discord import PCMVolumeTransformer, AudioSource, FFmpegPCMAudio
from typing import Union, Dict
from io import BufferedIOBase
from .constants import FFMPEG_OPTS


class Audio(PCMVolumeTransformer[AudioSource]):
    def __init__(self, stream: Union[str, BufferedIOBase], volume: float=0.5, *, opts: Dict[str, str]=FFMPEG_OPTS):
        source = FFmpegPCMAudio(stream, **opts)
        super().__init__(source, volume)
        self.done = 0

    def read(self):
        self.done += 20
        return super().read()