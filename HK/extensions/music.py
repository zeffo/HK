from typing import Optional
import discord
import asyncio
from discord.ext import commands
import yt_dlp
from ..paginator import Paginator, Unit
from os import getenv
import re
from io import StringIO
import json
from collections import namedtuple

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
    VIDEO = r'^(?:https?:\/\/)?(?:www\.)?(?:youtu\.be\/|youtube\.com\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=))((\w|-){11})(?:\S+)?$'
    PLAYLIST = r'^.*(youtu.be\/|list=)([^#\&\?]*).*'

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
        if match := re.match(cls.VIDEO, query):
            data = await cls()._get(match.groups()[0])
            return [Track(data['id'], data)]
        elif re.match(cls.PLAYLIST, query):
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
        self.repeat = False

    async def get(self):
        item = await super().get()
        if self.repeat:
            await self.put(item)
        return item

    async def play(self):
        if vc := self.guild.voice_client:
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

        if self.lock.locked() and len(tracks) == 1:
            track = tracks[0]
            embed = track.embed()
            embed.set_author(name="Queued")
            await track.ctx.send(embed=embed)
        elif len(tracks) > 1:
            await track.ctx.send(embed=discord.Embed(title=f"Queued {len(tracks)} items!"))

        if len(self._queue) == len(tracks) and not self.lock.locked():
            await self.play()
        
class MusicError(Exception):
    """Base exception for this extension"""

class Playlist:
    playlist = namedtuple('Playlist', ['name', 'owner', 'uses'])
    track = namedtuple('Track', ['id', 'title', 'stream'])
    def __init__(self, pool):
        self.pool = pool

    async def find(self, name, owner):
        async with self.pool.acquire() as con:
            data = await con.fetch('''
                SELECT Playlists.name, Playlists.owner, Playlists.uses, Tracks.title, Tracks.stream, Tracks.id
                FROM PlaylistTrackRelation 
                INNER JOIN Playlists ON Playlists.id=playlist
                INNER JOIN Tracks ON Tracks.id=track
                WHERE Playlists.name=$1 AND Playlists.owner=$2;
            ''', 
            name, owner)
        
        if data:
            rec = data[0]
            playlist = self.playlist(rec["name"], rec["owner"], rec["uses"])
            tracks = [self.track(d['id'], d['title'], d['stream']) for d in data]
            return playlist, tracks
        
        raise MusicError("That playlist doesn't exist!")

    async def new(self, name, owner, tracks):
        async with self.pool.acquire() as con:
            await con.execute('INSERT INTO Playlists (name, owner) VALUES ($1, $2) ON CONFLICT DO NOTHING;', name, owner)
            _id = (await con.fetch('SELECT id FROM Playlists WHERE name=$1 AND owner=$2;', name, owner))[0]['id']
            await con.executemany('INSERT INTO Tracks VALUES ($1, $2, $3) ON CONFLICT DO NOTHING', tracks)
            await con.executemany('INSERT INTO PlaylistTrackRelation (track, playlist) VALUES ($1, $2) ON CONFLICT DO NOTHING', [(t.id, _id) for t in tracks])

    async def remove(self, name, owner, tracks):
        async with self.pool.acquire() as con:
            if data := await con.fetch('SELECT id FROM Playlists WHERE name=$1 AND owner=$2;', name, owner):
                _id = data[0]['id']
                return await con.fetch('DELETE FROM PlaylistTrackRelation WHERE track = ANY($1::text[]) AND playlist = $2 RETURNING *', [t.id for t in tracks], _id)
            else:
                raise MusicError("That playlist doesn't exist!")

    async def delete(self, name, owner):
        async with self.pool.acquire() as con:
            if _id := await con.fetch('DELETE FROM Playlists WHERE name=$1 AND owner=$2 RETURNING id;', name, owner):
                await con.execute('DELETE FROM PlaylistTrackRelation WHERE playlist=$1', _id[0]["id"])
            else:
                raise MusicError("That playlist doesn't exist!")
        
    @staticmethod
    async def parse(tracks):
        parsed, err = [], []
        for track in tracks:
            if match := re.match(YTDL.VIDEO, track):
                parsed.append(match.groups()[0])
            else:
                err.append(track)
        if not parsed:
            raise MusicError("Couldn't parse those videos!")
        parsed = await asyncio.gather(*[YTDL()._get(i) for i in parsed])
        return [Playlist.track(d['id'], d['title'], d['url']) for d in parsed], err


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
        error = getattr(error, "original", error)
        if isinstance(error, MusicError):
            await ctx.send(embed=discord.Embed(description=error))
        elif isinstance(error, KeyError):
            await ctx.send(embed=discord.Embed(description="Couldn't retrieve that song!"))
        else:
            ctx.command = None
            await self.bot.get_cog('Errors').on_command_error(ctx, error)

    @commands.command(description="Plays a song from youtube.")
    async def play(self, ctx, *, query):
        queue, vc = await self.prepare(ctx)
        tracks = await YTDL.get(query, self.bot._session)
        for track in tracks:
            track.ctx = ctx
        await queue.add(tracks)

    @commands.command(description="Skips the current song.")
    async def skip(self, ctx):
        queue, vc = await self.prepare(ctx)
        vc.stop()

    @commands.command(description="Displays the enqueued songs.")
    async def queue(self, ctx):
        queue = self[ctx.guild]
        items = list(queue._queue)
        units = []
        if (np := queue.lock.track) and (vc := ctx.guild.voice_client):
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

        if queue.repeat:
            for unit in units:
                unit.embed.set_footer(text='(Loop enabled)')
        
        if len(units) == 1:
            await ctx.send(embed=units[0].embed)
        elif len(units) > 1:
            await ctx.send(embed=units[0].embed, view=Paginator(ctx, units=units))
        else:
            await ctx.send("The queue is empty!")

    @commands.command(description="Disconnects the bot from the VC and resets the queue.")
    async def dc(self, ctx):
        if vc := ctx.voice_client:
            vc.stop()
            await vc.disconnect()
        if ctx.guild.id in self.queues:
            del self.queues[ctx.guild.id]

    @commands.command(description="Sets to the volume (1-100)")
    async def volume(self, ctx, volume: float):
        queue = self[ctx.guild]
        queue.set_volume(volume/100)

    @commands.command(description="Sends a raw payload, for debugging purposes.")
    async def raw(self, ctx, *, query):
        yd = YTDL(fast=False)
        session = self.bot._session
        if match := re.match(r'^(?:https?:\/\/)?(?:www\.)?(?:youtu\.be\/|youtube\.com\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=))((\w|-){11})(?:\S+)?$', query):
            data = await yd._get(match.groups()[0])
        elif re.match(r'^.*(youtu.be\/|list=)([^#\&\?]*).*', query):
            data = await yd._get(query)
        else:
            data = await yd.from_api(session, query)
        
        data = [data["url"], data["title"], data["id"]]
        buffer = StringIO(json.dumps(data, indent=4))
        await ctx.send(file=discord.File(buffer, "data.json"))

    @commands.command(description="Pauses the current song.")
    async def pause(self, ctx):
        if ctx.voice_client:
            ctx.voice_client.pause()

    @commands.command(description="Resumes the current song if paused.")
    async def resume(self, ctx):
        if ctx.voice_client:
            ctx.voice_client.resume()

    @commands.command(description="Removes the song at the given position from the queue.")
    async def dequeue(self, ctx, index: int):
        queue = self[ctx.guild]._queue
        if index >= len(queue):
            raise MusicError("No track at that position!")
        else:
            embed = queue[index].embed()
            embed.set_author(name="Removed")
            await ctx.send(embed=embed)
            del queue[index]

    @commands.command(description="Toggles looping for the queue.")
    async def loop(self, ctx):
        queue = self[ctx.guild]
        queue.repeat = not queue.repeat
        await ctx.send(f"Queue looping {'enabled' if queue.repeat else 'disabled'}.")

    @commands.command(description="Lists your playlists, or of a member if provided.")
    async def playlists(self, ctx, author: Optional[discord.Member]):
        async with self.bot.pool.acquire() as con:
            playlists = await con.fetch('SELECT name FROM Playlists WHERE owner=$1', author.id)
            tracks = await con.fetch('SELECT COUNT(*) FROM (SELECT DISTINCT Tracks.id FROM PlaylistTrackRelation INNER JOIN Playlists ON playlist=Playlists.id INNER JOIN Tracks ON track=Tracks.id WHERE Playlists.owner=$1) AS temp;', author.id)
            if not playlists:
                raise MusicError("You haven't created any playlists!")
            embed = discord.Embed(title=f"{author.name}'s Playlists")
            embed.description = f"{len(playlists)} playlists, {tracks[0]['count']} unique tracks."
            units = [Unit(embed=embed)]
            for i in range(0, len(playlists), 10):
                e = discord.Embed()
                chunk = playlists[i:i+10]
                desc = "\n".join(f"{x+i}. {p['name']}" for x, p in enumerate(chunk))
                e.description = f"```md\n{desc}\n```"
                units.append(Unit(embed=e))
            await ctx.send(embed=embed, view=Paginator(ctx, units=units))



    @commands.group(invoke_without_command=True, description="Displays the contents of a playlist.")
    async def playlist(self, ctx, author: Optional[discord.Member], *, name):
        author = author or ctx.author
        playlist, tracks = await Playlist(self.bot.pool).find(name, author.id)
        embed = discord.Embed(title=playlist.name)
        embed.set_author(name=f"Playlist by {author.name}")
        embed.description = f"Tracks: {len(tracks)}"
        units = [Unit(embed=embed)]
        for i in range(0, len(tracks), 10):
            chunk = tracks[i:i+10]
            e = discord.Embed(title="Tracks")
            desc = "\n".join(f"{x+i}. {t.title}" for x, t in enumerate(chunk))
            e.description = f"```md\n{desc}\n```"
            units.append(Unit(embed=e))
        await ctx.send(embed=embed, view=Paginator(ctx, units=units))

    @playlist.command(description="Plays a playlist.")
    async def play(self, ctx, author: Optional[discord.Member], *, name):
        author = author or ctx.author
        _, tracks = await Playlist(self.bot.pool).find(name, author.id)
        queue, _ = await self.prepare(ctx)
        tracks = [Track(d['id'], d) for d in await asyncio.gather(*[YTDL()._get(t.id) for t in tracks])]
        for track in tracks:
            track.ctx = ctx
        await queue.add(tracks)

    @playlist.command(description="Creates a playlist.")
    async def create(self, ctx, name, *tracks):
        m = await ctx.send("Parsing tracks, please wait...")
        parsed, err = await Playlist.parse(tracks)
        await Playlist(self.bot.pool).new(name, ctx.author.id, parsed)
        ret = f"Created Playlist {name} with {len(parsed)}/{len(tracks)} tracks. "
        if err:
            ret += f"I was unable to parse the following: {', '.join(err)}"
        await m.edit(content=ret)

    @playlist.command(description="Adds tracks to a playlist.")
    async def add(self, ctx, name, *tracks):
        parsed, err = await Playlist.parse(tracks)
        await Playlist(self.bot.pool).new(name, ctx.author.id, parsed)
        ret = f"Edited Playlist {name}, added {len(parsed)}/{len(tracks)} tracks. "
        if err:
            ret += f"I was unable to parse the following: {', '.join(err)}"
        await ctx.send(ret)

    @playlist.command(description="Removes tracks from a playlist.")
    async def remove(self, ctx, name, *tracks):
        parsed, err = await Playlist.parse(tracks)
        deleted = await Playlist(self.bot.pool).remove(name, ctx.author.id, parsed)
        await ctx.send(f"Deleted {len(deleted)} tracks.")

    @playlist.command(description="Deletes a playlist.")
    async def delete(self, ctx, *, name):
        await Playlist(self.bot.pool).delete(name, ctx.author.id)
        await ctx.send(f"Deleted playlist {name}.")
        

def setup(bot):
    bot.add_cog(Music(bot))
