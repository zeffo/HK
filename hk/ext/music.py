from discord.ext import commands
from discord import Embed, Guild, Member, VoiceClient
from typing import Any, Dict, Tuple

from ..models.music import Track, MediaPlayer, MusicError, DownloadError, Queue
from ..models.bot import Bot
from ..models.context import Context


def validate_voice():
    """Decorator to validate a member's voice state"""
    async def check(ctx: Context):
        if isinstance(ctx.author, Member) and ctx.guild:
            channel = getattr(ctx.author.voice, 'channel', None)
            vchannel = getattr(ctx.guild.voice_client, 'channel', None)
            vclient = ctx.guild.voice_client
            if not channel:
                raise MusicError("You must be in a Voice Channel!")
            elif vchannel is not None and vchannel != channel:
                if len(vchannel.members) == 1:
                    if isinstance(vclient, VoiceClient):
                        await vclient.move_to(channel)
                    return True
                else:
                    MusicError("You must be in the same Voice Channel as the bot!")
        return True
    return commands.check(check)


class Music(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.token = bot.conf.youtube_api_token
        self.queues: Dict[Guild, Queue] = {}

    @commands.command()
    async def search(self, ctx: Context, *, query: str) -> Any:
        tracks = await Track.from_query(query, session=self.bot.session, token=self.token)
        await ctx.send(embed=tracks[0].embed(), view=MediaPlayer(ctx, tracks))

    async def prepare(self, ctx: Context) -> Tuple[Queue, VoiceClient]:
        vc = await ctx.connect()
        if not ctx.guild or vc is None:
            raise MusicError("No Voice Channel to join!")
        queue = self.queues.setdefault(ctx.guild, Queue(ctx.guild, self.bot, broadcast=ctx.channel))   
        vc = VoiceClient(vc.client, vc.channel)    
        return queue, vc

    @commands.command()
    @validate_voice()
    async def play(self, ctx: Context, *, query: str):
        queue, _ = await self.prepare(ctx)
        tracks = await Track.from_query(query, session=self.bot.session, token=self.token)
        await queue.add(tracks[0])

        

    @commands.Cog.listener()
    async def on_command_error(self, ctx: Context, error: Exception):
        error = getattr(error, "original", error)
        if isinstance(error, MusicError):
            await ctx.send(embed=Embed(description=error))
        elif isinstance(error, KeyError):
            await ctx.send(
                embed=Embed(description="Couldn't retrieve that song!")
            )
        elif isinstance(error, DownloadError):
            await ctx.send(
                embed=Embed(description="Couldn't download that song!")
            )
        else:
            ctx.skip = True # Propogate error to Errors.on_command_error


async def setup(bot: Bot):
    await bot.add_cog(Music(bot))
