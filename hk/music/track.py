from __future__ import annotations

import asyncio
from html import unescape
from io import BytesIO
from textwrap import wrap
from typing import Any, Dict, List, Optional, Tuple, TypedDict

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
    "Banner",
)


class ThumbnailMixin:
    id: str
    title: str
    uploader: str
    thumbnails: List[Thumbnail]

    def get_thumbnail(self):
        return self.thumbnails[-1]["url"]

    async def create_banner(self, session: ClientSession):
        return await Banner.create(self, session=session)


cache: Dict[str, Banner] = {}


class Banner:
    def __init__(
        self,
        track: ThumbnailMixin,
        background: Tuple[int, int, int],
        fill: Tuple[int, int, int],
        image: Image.Image,
    ):
        self.track = track
        self.background = background
        self.fill = fill
        self.image = image
        self._embed = Embed(color=Color.from_rgb(*self.background)).set_image(
            url="attachment://track.png"
        )
        cache[track.id] = self

    @property
    def embed(self):
        return self._embed.copy()

    @staticmethod
    def get_palette(
        file: BytesIO,
    ) -> Tuple[Tuple[int, int, int], List[Tuple[int, int, int]]]:
        cf = ColorThief(file)
        return cf.get_color(100), cf.get_palette(15, 100)  # type: ignore

    @staticmethod
    def ambience(color: Tuple[int, int, int]) -> float:
        return (0.299 * color[0] + 0.587 * color[1] + 0.114 * color[2]) / 255

    @staticmethod
    def contrasting(color: Tuple[int, int, int]):
        d = 0 if Banner.ambience(color) > 0.5 else 255
        return (d, d, d)

    @staticmethod
    def generate(
        track: ThumbnailMixin,
        buffer: BytesIO,
        *,
        normal: str = "static/font.otf",
        bold: str = "static/bold.otf",
    ):
        x, y = 900, 300  # canvas size
        base, palette = Banner.get_palette(buffer)
        fill = max(
            palette, key=lambda c: abs(Banner.ambience(base) - Banner.ambience(c))
        )
        if abs(Banner.ambience(fill) - Banner.ambience(base)) < 0.3:
            fill = Banner.contrasting(base)
        gradient = Image.new("RGB", (x, y), base)
        tx, ty = 250, 170
        thumbnail = Image.open(buffer).resize((tx, ty))
        gap = (y - ty) // 2
        gradient.paste(thumbnail, (50, gap))
        pen = ImageDraw.Draw(gradient)
        _normal = ImageFont.truetype(normal, 20)
        _bold = ImageFont.truetype(bold, 40)
        title = "\n".join(wrap(track.title, 24, max_lines=2))
        uploader = "By " + track.uploader
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
        return Banner(track, base, fill, gradient)

    def file(self):
        buffer = BytesIO()
        self.image.save(buffer, format="png")
        buffer.seek(0)
        return File(buffer, filename="track.png")

    @classmethod
    async def create(cls, track: ThumbnailMixin, *, session: ClientSession):
        if banner := cache.get(track.id):
            return banner
        async with session.get(track.get_thumbnail()) as resp:
            buffer = BytesIO(await resp.content.read())
        return await asyncio.to_thread(Banner.generate, track, buffer)


class Thumbnail(TypedDict):
    url: str


class BaseTrack(ThumbnailMixin, BaseModel):
    id: str
    title: str
    description: Optional[str]
    uploader: str
    thumbnails: List[Thumbnail]


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


class BasePlaylist(ThumbnailMixin, BaseModel):
    id: str
    title: str
    uploader: str = "Unknown Uploader"
    thumbnails: List[Thumbnail]
    entries: List[BaseTrack]

    def __init__(self, **data: Any):
        data["uploader"] = data["uploader"] or "Unknown Uploader"
        super().__init__(**data)


class Playlist(BasePlaylist):
    ...
