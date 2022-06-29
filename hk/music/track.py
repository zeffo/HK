from __future__ import annotations

import asyncio
from html import unescape
from io import BytesIO
from textwrap import wrap
from typing import Any, Dict, List, Optional, Tuple, Union

from aiohttp import ClientSession
from colorthief import ColorThief
from discord import Color, Embed, File
from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel

__all__ = (
    "BaseTrack",
    "Track",
    "APIItem",
    "APIResult",
    "BasePlaylist",
    "Playlist",
    "ThumbnailCreator",
)


class ThumbnailCache(type):
    cache: Dict[str, Tuple[Embed, Image.Image]] = {}


class ThumbnailCreator(metaclass=ThumbnailCache):
    def __init__(self, track: Union[BaseTrack, BasePlaylist]):
        self.track = track
        self.url = track.get_thumbnail()

    def get_palette(
        self, file: BytesIO
    ) -> Tuple[Tuple[int, int, int], List[Tuple[int, int, int]]]:
        cf = ColorThief(file)
        return cf.get_color(100), cf.get_palette(15, 100)  # type: ignore

    def ambience(self, color: Tuple[int, int, int]) -> float:
        return (0.299 * color[0] + 0.587 * color[1] + 0.114 * color[2]) / 255

    def contrasting(self, color: Tuple[int, int, int]):
        d = 0 if self.ambience(color) > 0.5 else 255
        return (d, d, d)

    def generate(
        self,
        buffer: BytesIO,
        *,
        normal: str = "static/font.otf",
        bold: str = "static/bold.otf",
    ):
        x, y = 900, 300  # canvas size
        base, palette = self.get_palette(buffer)
        fill = max(palette, key=lambda c: abs(self.ambience(base) - self.ambience(c)))
        if abs(self.ambience(fill) - self.ambience(base)) < 0.3:
            fill = self.contrasting(base)
        gradient = Image.new("RGB", (x, y), base)
        tx, ty = 250, 170
        thumbnail = Image.open(buffer).resize((tx, ty))
        gap = (y - ty) // 2
        gradient.paste(thumbnail, (50, gap))
        pen = ImageDraw.Draw(gradient)
        _normal = ImageFont.truetype(normal, 20)
        _bold = ImageFont.truetype(bold, 40)
        title = "\n".join(wrap(self.track.title, 25, max_lines=2))
        uploader = "By " + self.track.uploader
        start = tx + gap
        tbox = pen.multiline_textbbox((start, gap), title, font=_bold, spacing=20)
        ubox = pen.textbbox((start, tbox[3] + gap / 2), uploader, font=_normal)
        cy = (y - (ubox[3] - tbox[1])) / 2  # centred y coordinate for title
        titlex = ((x - start) - (tbox[2] - tbox[0])) / 3 + start
        pen.multiline_text((titlex, cy), title, fill=fill, font=_bold)
        pen.text(
            (titlex, cy + (tbox[-1] - tbox[1]) + gap / 2),
            uploader,
            font=_normal,
            fill=fill,
        )
        file = self.save(gradient)
        embed = Embed(color=Color.from_rgb(*base))
        embed.set_image(url="attachment://track.png")
        self.__class__.cache[self.track.id] = embed, gradient
        return embed, file

    def save(self, image: Image.Image):
        buffer = BytesIO()
        image.save(buffer, format="png")
        buffer.seek(0)
        return File(buffer, filename="track.png")

    async def create(self, *, session: ClientSession):
        if cached := self.__class__.cache.get(self.track.id):
            embed, image = cached
            return embed, self.save(image)
        async with session.get(self.url) as resp:
            buffer = BytesIO(await resp.content.read())
        embed, file = await asyncio.to_thread(self.generate, buffer)
        return embed, file


class Thumbnail(BaseModel):
    url: str

    def __str__(self):
        return f"Thumbnail({self.url})"


class BaseTrack(BaseModel):
    id: str
    title: str
    description: Optional[str]
    uploader: str
    thumbnails: List[Thumbnail]

    async def create_thumbnail(self, session: ClientSession):
        return await ThumbnailCreator(self).create(session=session)

    def get_thumbnail(self):
        return self.thumbnails[-1].url


class Track(BaseTrack):
    """Represents a video on YouTube with minimal information"""

    url: str
    duration: float
    uploader: str
    thumbnails: List[Thumbnail]
    thumbnail: str

    def get_thumbnail(self):
        return self.thumbnail

    def __str__(self):
        return f"Track(title={self.title}, uploader={self.uploader})"

    @property
    def runtime(self):
        m = self.duration / 60
        return f"{m:.2f} minutes"


class APISnippet(BaseModel):
    def __init__(self, **data: Any) -> None:
        for key, value in data.items():
            data[key] = unescape(value)
        super().__init__(**data)

    title: str
    description: Optional[str]
    thumbnails: Dict[str, Thumbnail]
    channelTitle: str

    @property
    def uploader(self):
        return self.channelTitle

    def __str__(self):
        return f"APISnippet(title={self.title}, channel={self.channelTitle})"


class ID(BaseModel):
    kind: str
    videoId: str

    def __str__(self):
        return self.videoId


class APIItem(BaseModel):
    id: ID
    snippet: APISnippet

    def __str__(self):
        return f"APIItem(id={self.id}, snippet={self.snippet})"


class APIResult(BaseModel):
    items: List[APIItem]

    def __str__(self):
        return f"APIResult(items={len(self.items)})"

    def partials(self):
        tracks: List[BaseTrack] = []
        for item in self.items:
            snip = item.snippet
            thumbnails = [snip.thumbnails[k] for k in snip.thumbnails]
            tracks.append(
                BaseTrack(
                    id=str(item.id),
                    title=snip.title,
                    description=snip.description,
                    thumbnails=thumbnails,
                    uploader=snip.uploader,
                )
            )
        return tracks


class BasePlaylist(BaseModel):
    id: str
    title: str
    uploader: str = "Unknown Uploader"
    thumbnails: List[Thumbnail]
    entries: List[BaseTrack]

    def __init__(self, **data: Any):
        data['uploader'] = data['uploader'] or "Unknown Uploader"
        super().__init__(**data)

    async def create_thumbnail(self, session: ClientSession):
        return await ThumbnailCreator(self).create(session=session)

    def get_thumbnail(self):
        return self.thumbnails[-1].url




class Playlist(BasePlaylist):
    def __str__(self):
        return f"Playlist(title={self.title}, uploader={self.uploader}, tracks={len(self.entries)})"
