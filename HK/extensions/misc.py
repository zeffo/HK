from discord.ext import commands
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..__main__ import Bot

class Miscellaneous(commands.Cog):
    def __init__(self, bot):
        self.bot: Bot = bot

    @commands.command()
    async def source(self, ctx):
        await ctx.send(embed=self.bot.embed(title="Source", description="https://github.com/zeffo/HK"))


def setup(bot):
    bot.add_cog(Miscellaneous(bot))