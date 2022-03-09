import discord
import asyncio
from discord.ext import commands
import yt_dlp
from ..paginator import Paginator, Unit
from os import getenv
import re
from io import StringIO
import json

class Track:
    __slots__ = ('id', 'data', 'title', 'description', 'duration', 'uploader', 'url', 'ctx')
    def __init__(self, _id, data=None):
        self.id = _id
        self.data = data
        self.ctx = None
        for item in self.__slots__[2:-1]:
            setattr(self, item, data[item])

    @property
    def thumbnail(self):
        return self.data['thumbnails'][-1]["url"]

    @property
    def stream(self):
        return self.data['url']

    def __matmul__(self, ytdl):
        async def update():
            self.data = await ytdl._get(self.id)
        return update()

    def embed(self):
        e = discord.Embed(title=self.title, url=self.data.get('webpage_url', discord.embeds.EmptyEmbed))
        e.set_author(name="Now Playing")
        e.set_thumbnail(url=self.thumbnail)
        if self.ctx:
            e.set_footer(text=f"Requested by {self.ctx.author}", icon_url=self.ctx.author.display_avatar.url)

        return e


class YTDL(yt_dlp.YoutubeDL):
    SEARCH = f"https://www.googleapis.com/youtube/v3/search?part=snippet&maxResults=1&q={{0}}&type=video&key={getenv('YOUTUBE_API_KEY')}"
    PARAMS = {
            'format': 'bestaudio',
            'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
            'restrictfilenames': True,
            'noplaylist': False,
            'nocheckcertificate': True,
            'ignoreerrors': False,
            'logtostderr': False,
            'quiet': True,
            'no_warnings': True,
            'default_search': 'auto',
            'source_address': '0.0.0.0',
        }

    def __init__(self, fast=True):
        params = self.PARAMS
        if fast:
            params.update({'extract_flat': True, 'skip_download': True})
        super().__init__(params)

    async def _get(self, url):
        def to_thread():
            with self as yd:
                data = yd.extract_info(url, download=False)
            return data
        return await asyncio.get_running_loop().run_in_executor(None, to_thread)

    async def from_api(self, session, query):
        async with session.get(self.SEARCH.format(query)) as resp:
            data = await resp.json()
            return await self._get(data["items"][0]["id"]["videoId"])

    @classmethod
    async def get(cls, query, session):
        if match := re.match(r'^(?:https?:\/\/)?(?:www\.)?(?:youtu\.be\/|youtube\.com\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=))((\w|-){11})(?:\S+)?$', query):
            data = await cls()._get(match.groups()[0])
            return [Track(data['id'], data)]
        elif re.match(r'^.*(youtu.be\/|list=)([^#\&\?]*).*', query):
            data = await cls()._get(query)
            return [Track(d['id'], d) for d in data['entries']]
        else:
            data = await cls().from_api(session, query)
            return [Track(data['id'], data)]


class Audio(discord.PCMVolumeTransformer):
    def __init__(self, source, volume=0.5):
        super().__init__(source, volume)
        self.done = 0
    
    def read(self):
        self.done += 20
        return super().read()
        
class Lock(asyncio.Lock):
    track = None

    async def acquire(self, track):
        self.track = track
        await super().acquire()
            
class Queue(asyncio.Queue):
    def __init__(self, guild: discord.Guild, loop, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if loop is None:
            loop = asyncio.get_event_loop()
        self.guild = guild
        self.loop = loop
        self.lock = Lock()
        self.volume = 0.5

    async def play(self):
        vc = self.guild.voice_client
        track = await self.get()
        await self.lock.acquire(track)
        await (track @ YTDL(fast=False))
        await track.ctx.send(embed=track.embed())
        source = Audio(discord.FFmpegPCMAudio(track.stream, **{"before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5","options": "-vn"}), volume=self.volume)
        vc.play(source, after=lambda e: self.loop.create_task(self.next(e)))

    def set_volume(self, volume):
        self.volume = volume
        if self.lock.locked():
            self.guild.voice_client.source.volume = volume

    async def next(self, error=None):
        self.lock.release()
        await self.play()
    
    async def add(self, tracks):
        for track in tracks:
            self.put_nowait(track)

        if self.lock.locked():
            if len(tracks) == 1:
                track = tracks[0]
                embed = track.embed()
                embed.set_author(name="Queued")
                await track.ctx.send(embed=embed)
            else:
                await track.ctx.send(embed=discord.Embed(title=f"Queued {len(tracks)} items!"))

        if len(self._queue) == len(tracks) and not self.lock.locked():
            await self.play()


        
class MusicError(Exception):
    """Base exception for this extension"""

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queues = {}

    def __getitem__(self, g):
        return self.queues.setdefault(g.id, Queue(g, loop=self.bot.loop))

    async def prepare(self, ctx):
        queue = self[ctx.guild]
        vc = await ctx.connect()
        if vc is None:
            raise MusicError("No voice channel to join!")
        return queue, vc

    async def cog_command_error(self, ctx, error) -> None:
        if isinstance(error, MusicError):
            await ctx.send(embed=discord.Embed(description=error))
        elif isinstance(error, KeyError):
            await ctx.send(embed=discord.Embed(description="Couldn't retrieve that song!"))
        else:
            raise error

    @commands.command()
    async def play(self, ctx, *, query):
        queue, vc = await self.prepare(ctx)
        tracks = await YTDL.get(query, self.bot._session)
        for track in tracks:
            track.ctx = ctx
        await queue.add(tracks)

    @commands.command()
    async def skip(self, ctx):
        queue, vc = await self.prepare(ctx)
        vc.stop()

    @commands.command()
    async def queue(self, ctx):
        queue, vc = await self.prepare(ctx)
        items = list(queue._queue)
        units = []  
        if np := queue.lock.track:
            e = np.embed()
            e.set_author(name="Now Playing: ")
            e.description = f"`{vc.source.done//1000}/{np.duration}s`"
            units.append(Unit(embed=e))

        for i in range(0, len(items), 10):
            embed = discord.Embed(title="Queue")
            chunk = items[i:i+10]
            tracks = "\n".join([f"{x+i}. {t.title}" for x, t in enumerate(chunk)])
            embed.description = f"```md\n{tracks}```"
            units.append(Unit(embed=embed))
        
        if len(units) == 1:
            await ctx.send(embed=units[0].embed)
        elif len(units) > 1:
            await ctx.send(embed=units[0].embed, view=Paginator(ctx, units=units))
        else:
            await ctx.send("The queue is empty!")

    @commands.command()
    async def dc(self, ctx):
        if vc := ctx.voice_client:
            vc.stop()
            await vc.disconnect()
        if ctx.guild.id in self.queues:
            del self.queues[ctx.guild.id]

    @commands.command()
    async def volume(self, ctx, volume: float):
        queue = self[ctx.guild]
        queue.set_volume(volume/100)

    @commands.command()
    async def raw(self, ctx, *, query):
        yd = YTDL(fast=False)
        session = self.bot._session
        if match := re.match(r'^(?:https?:\/\/)?(?:www\.)?(?:youtu\.be\/|youtube\.com\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=))((\w|-){11})(?:\S+)?$', query):
            data = await yd._get(match.groups()[0])
        elif re.match(r'^.*(youtu.be\/|list=)([^#\&\?]*).*', query):
            data = await yd._get(query)
        else:
            data = await yd.from_api(session, query)
        buffer = StringIO(json.dumps(data, indent=4))
        await ctx.send(file=discord.File(buffer, "data.json"))

    @commands.command()
    async def pause(self, ctx):
        if ctx.voice_client:
            ctx.voice_client.pause()

    @commands.command()
    async def resume(self, ctx):
        if ctx.voice_client:
            ctx.voice_client.resume()

    @commands.command()
    async def dequeue(self, ctx, index: int):
        queue = self[ctx.guild]._queue
        if index >= len(queue):
            raise MusicError("No track at that position!")
        else:
            embed = queue[index].embed()
            embed.set_author(name="Removed")
            await ctx.send(embed=embed)
            del queue[index]
        

def setup(bot):
    bot.add_cog(Music(bot))
