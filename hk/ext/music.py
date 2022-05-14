from asyncio import get_running_loop
from discord import TextChannel, app_commands
from discord.ext import commands
from discord import Embed, Guild, Interaction, Member, VoiceClient
from typing import Dict, Tuple, Optional

from ..models.music import Track, MusicError, DownloadError, Queue
from ..models.bot import Bot
from ..models.context import Context


def validate_voice():
    """Decorator to validate a member's voice state"""
    async def check(interaction: Interaction):
        if isinstance(interaction.user, Member) and interaction.guild:
            channel = getattr(interaction.user.voice, 'channel', None)
            vchannel = getattr(interaction.guild.voice_client, 'channel', None)
            vclient = interaction.guild.voice_client
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
    return app_commands.check(check)


class Music(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.token = bot.conf.youtube_api_token
        self.queues: Dict[Guild, Queue] = {}

    async def connect(self, interaction: Interaction) -> Optional[VoiceClient]:
        """Return the current voice client, or attempt to join the author's voice channel."""
        guild = interaction.guild
        if not guild:
            return
        if guild.voice_client is not None and getattr(
            guild.voice_client, "channel", None
        ):
            if isinstance(guild.voice_client, VoiceClient):
                return guild.voice_client
        elif isinstance(interaction.user, Member) and interaction.user.voice:
            if vc := interaction.user.voice.channel:
                return await vc.connect()

    async def prepare(self, interaction: Interaction) -> Tuple[Queue, VoiceClient]:
        vc = await self.connect(interaction)
        if not interaction.guild or vc is None:
            raise MusicError("No Voice Channel to join!")
        broadcast = interaction.channel if isinstance(interaction.channel, TextChannel) else None
        queue = self.queues.setdefault(interaction.guild, Queue(interaction.guild, self.bot, broadcast=broadcast, loop=get_running_loop()))   
        vc = VoiceClient(vc.client, vc.channel)    
        return queue, vc

    @app_commands.command()
    @app_commands.describe(query="The song or playlist to play. Can be a YouTube URL.")
    @app_commands.guilds(489635674987692042)
    @validate_voice()
    async def play(self, interaction: Interaction, query: str):
        """Plays a song or playlist"""
        await interaction.response.defer(ephemeral=True)
        queue, _ = await self.prepare(interaction)
        tracks = await Track.from_query(query, session=self.bot.session, token=self.token)
        await queue.add(*tracks)

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
