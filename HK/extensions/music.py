import pafy
import asyncio
import re

from discord import FFmpegPCMAudio, PCMVolumeTransformer
from discord.ext import commands
from functools import partial, wraps
from textwrap import shorten
from os import getenv

from ..paginator import Paginator, Unit

YOUTUBE_SEARCH_ENDPOINT = 'https://www.googleapis.com/youtube/v3/search?part=snippet&maxResults=1&q={0}&type=video&key={1}'
YOUTUBE_SONG_URL = 'https://www.youtube.com/watch?v={0}'
FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}  
YT_API_KEY = getenv('YOUTUBE_API_KEY')

class CustomAudio(PCMVolumeTransformer):
    played = 0

    def read(self):
        self.played += 20
        return super().read()

class NoVoiceState(Exception):
    """ Raised when a member does not have a VoiceState """

class Track:
    def __init__(self, ctx, query, *, pafy=None) -> None:
        self.query = query
        self.ctx = ctx
        self.pafy = pafy

    def thread(func):
        """ Runs a function in another thread, returns a Future """
        @wraps(func)
        def wrapper(*args, **kwargs) -> asyncio.Future:
            return args[0].ctx.bot.loop.run_in_executor(None, partial(func, *args, **kwargs))
        return wrapper

    @thread
    def audio(self):
        if self.pafy:
            return self.pafy.getbestaudio().url_https

    @thread
    def _new(self, url=None):
        url = url or self.query
        self.pafy = pafy.new(url)
        return self.pafy

    @classmethod
    async def get(cls, ctx, query):
        track = cls(ctx, query)
        if re.match(r'^(https?\:\/\/)?(www\.)?(youtube\.com|youtu\.?be)\/.+$', query):
            await track._new()
        else:
            async with ctx.bot.cs.get(YOUTUBE_SEARCH_ENDPOINT.format(query, YT_API_KEY)) as resp:
                data = await resp.json()
            await track._new(data["items"][0]["id"]["videoId"])
        return track

    @classmethod
    async def get_playlist_tracks(cls, ctx, url):
        tracks = []
        playlist = await ctx.bot.loop.run_in_executor(None, pafy.get_playlist2, url)
        for song in playlist:
            track = Track(ctx, url, pafy=song)
            tracks.append(track)
        return tracks


class Queue(asyncio.Queue):
    """Queue implementation to hold song order for each guild, as well as handle playback, looping and many other things."""

    def __init__(self, ctx):
        self.ctx = ctx
        self.playing = None
        self.looping = False
        self._loop_index = 0
        super().__init__()

    def embed(self, track):
        p = track.pafy
        e = self.ctx.bot.embed(title="Now Playing", description=p.title, color=self.ctx.bot.color)
        e.add_field(name='Duration', value=f'`{p.duration}`')
        e.add_field(name='Views', value=f'`{p.viewcount}`', inline=False)
        e.set_thumbnail(url=p.thumb)
        e.set_author(name=str(track.ctx.author.name), icon_url=str(track.ctx.author.avatar))
        return e

    async def play(self, track):
        source = FFmpegPCMAudio(await track.audio(), **FFMPEG_OPTIONS)
        stream = CustomAudio(source, volume=0.1)
        self.ctx.voice_client.play(stream, after=lambda _: self.ctx.bot.loop.create_task(self.next()))
        track.source = stream
        self.playing = track
        await self.ctx.send(embed=self.embed(track))

    async def next(self):
        if self.empty() or self.ctx.voice_client.is_playing():
            return
        if not self.looping:
            await self.play(await self.get())
        else:
            if self._loop_index == self.qsize() - 1:
                self._loop_index = 0
            else:
                self._loop_index += 1      
            await self.play(self._deque[self._loop_index])

    async def add(self, track):
        await self.put(track)
        if self.qsize() == 1 and not self.ctx.voice_client.is_playing():
            await self.next()

    async def add_tracks(self, *tracks):
        for track in tracks:
            await self.add(track)
    
class Error(Exception):
    """An elegant way to send exceptions to discord without messy if statements""" 


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queues = {}
        pafy.set_api_key(YT_API_KEY)
        self.EMPTY = Error("The queue is empty!")

    async def cog_command_error(self, ctx, error):
        error = getattr(error, 'original', error)
        if isinstance(error, Error):
            await ctx.send(str(error))
        else:
            raise error

    async def prepare_queue(self, ctx):
        try:
            await ctx.author.voice.channel.connect()
        except asyncio.TimeoutError:
            pass    # discord.py master raises TimeoutError for no reason (?) | Might have to remove later

        queue = Queue(ctx)
        self.queues[ctx.guild.id] = queue
        return queue

    @commands.command()
    async def play(self, ctx, *, query: str) -> None:
        async with ctx.typing(): 
            if not ctx.author.voice:
                raise NoVoiceState(ctx.author)
            if not ctx.guild.voice_client:
                queue = await self.prepare_queue(ctx)
            else:
                queue = self.queues[ctx.guild.id]

            if re.match(r'^(?!.*\?.*\bv=)https:\/\/www\.youtube\.com\/.*\?.*\blist=.*$', query):
                tracks = await Track.get_playlist_tracks(ctx, query)
                embed = ctx.bot.embed(title=f"Queued {len(tracks)} items!", color=ctx.bot.color)
                embed.clear_fields()
                await ctx.send(embed=embed)
                await queue.add_tracks(*tracks)
            else:
                track = await Track.get(ctx, query)
                embed = queue.embed(track)
                embed.clear_fields()
                embed.title="Queued!"
                await ctx.send(embed=embed)
                await queue.add(track)

    def get_queue(self, ctx, *, error=False):
        res = queue if ctx.voice_client and (queue := self.queues[ctx.guild.id]) else None
        if error and not res:
            raise self.EMPTY
        return res
        
    @commands.command()
    async def skip(self, ctx):
        queue = self.get_queue(ctx, error=True)
        if queue.playing:
            ctx.voice_client.stop()
            await queue.next()
        elif queue.empty():
            raise self.EMPTY
        await ctx.message.add_reaction('<:yes:866983565639942184>')
        

    @commands.command()
    async def volume(self, ctx, volume: int):
        if vc := ctx.voice_client:
            vc.source.volume = volume/100
            await ctx.send("Volume changed!")
        else:
            raise Error("There is no song playing!")

    @commands.command()
    async def goto(self, ctx, seconds: int):
        """Goes to the given second mark in the song."""
        if (queue := self.get_queue(ctx, error=True)) and queue.playing:
            ctx.voice_client.stop()
            source = FFmpegPCMAudio(await queue.playing.audio(), before_options=f"-ss {seconds}s "+FFMPEG_OPTIONS['before_options'], options=FFMPEG_OPTIONS['options'])
            stream = CustomAudio(source, volume=0.5)
            ctx.voice_client.play(stream, after=lambda _: self.bot.loop.create_task(queue.next()))
            await ctx.send(f"Went to {seconds} seconds!")

    @commands.command()
    async def queue(self, ctx):
        if queue := self.get_queue(ctx, error=True):
            units = []
            items = list(queue._queue)
            for index in range(0, len(items), 10):
                tracks = items[index:index+10]
                songs = [f"{i+1}. {shorten(track.pafy.title, 55)} [{track.pafy.length}s] ~ {track.ctx.author.mention}" for i, track in enumerate(tracks)]
                desc = "\n".join(songs)
                embed = ctx.bot.embed(title="Queue", description=desc, color=self.bot.color)
                units.append(Unit(embed=embed))
            np = queue.playing.pafy
            total = int(np.length)
            done = ctx.voice_client.source.played//1000
            desc = f"**Now Playing:** `{np.title} [{done}s/{np.length}s] [{round(done/total*100)}% complete]` ~ requested by {queue.playing.ctx.author.mention}\n"
            if units:
                units[0].embed.description = desc + units[0].embed.description
            else:
                units.append(Unit(embed=ctx.bot.embed(title="Queue", color=self.bot.color, description=desc)))
            await ctx.send(embed=units[0].embed, view=Paginator(ctx, units=units))

    @commands.command()
    async def nowplaying(self, ctx):
        if queue := self.get_queue(ctx, error=True):
            embed = queue.embed(queue.playing)
            total = int(queue.playing.pafy.length)
            done = ctx.voice_client.source.played//1000
            embed.add_field(name="Duration Left", value=f"`{total-done}s --> {round(done/total*100)}% complete ~ requested by {queue.playing.ctx.author.mention}`")
            await ctx.send(embed=embed)

    @commands.command()
    async def pause(self, ctx):
        if ctx.voice_client:
            ctx.voice_client.pause()
        
    @commands.command()
    async def resume(self, ctx):
        if ctx.voice_client:
            ctx.voice_client.resume()

    @commands.command()
    async def remove(self, ctx, index: int):
        '''Removes a song from the queue'''
        if queue := self.get_queue(ctx, error=True):
            if index <= queue.qsize():
                track = queue._queue[index-1]
                await ctx.send(f"Removed `{track.pafy.title}` from the queue!")
                del queue._queue[index-1]
            else:
                raise Error("There's no track at that index!")

    @commands.command()
    async def dc(self, ctx):
        if ctx.voice_client:
            ctx.voice_client.stop()
            await ctx.voice_client.disconnect()
        if self.get_queue(ctx, error=True):
            del self.queues[ctx.guild.id]

            

def setup(bot):
    bot.add_cog(Music(bot)) 