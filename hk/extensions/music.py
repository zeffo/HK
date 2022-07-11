from discord import Guild, Interaction
from discord import app_commands
from ..bot import Bot
from ..music import Queue, GuildOnlyException, YTDL, Voice
from ..protocols import GuildMessageable
from discord.ext import commands
from typing import Dict


class Music(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.queues: Dict[Guild, Queue] = {}

    def get_queue(self, iact: Interaction):
        if iact.guild and isinstance(iact.channel, GuildMessageable):
            return self.queues.setdefault(
                iact.guild, Queue(self.bot, bound=iact.channel)
            )
        raise GuildOnlyException

    @app_commands.command()
    async def play(self, iact: Interaction, query: str):
        vc = iact.guild.voice_client or await iact.user.voice.channel.connect(cls=Voice)  # type: ignore
        queue = self.get_queue(iact)
        track = await YTDL.from_query(
            query, session=self.bot.session, api_key=self.bot.conf.env["YOUTUBE"]
        )
        await queue.put(track[0])


async def setup(bot: Bot):
    await bot.add_cog(Music(bot))
