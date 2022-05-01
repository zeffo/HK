from discord.ext import commands
from typing import Any

from ..models.music import Track
from ..models.bot import Bot
from ..models.context import Context


class Music(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.token = bot.conf.youtube_api_token

    @commands.command()
    async def search(self, ctx: Context, *, query: str) -> Any:
        tracks = await Track.from_query(query, session=self.bot.session, token=self.token)
        await ctx.send("\n".join([t.title for t in tracks]))




async def setup(bot: Bot):
    await bot.add_cog(Music(bot))
