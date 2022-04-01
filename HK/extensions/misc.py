from discord.ext import commands
from discord import File
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..__main__ import Bot


class Miscellaneous(commands.Cog):
    def __init__(self, bot):
        self.bot: Bot = bot

    @commands.command()
    async def source(self, ctx):
        await ctx.send(
            embed=self.bot.embed(
                title="Source", description="https://github.com/zeffo/HK"
            )
        )

    @commands.command()
    @commands.is_owner()
    async def log(self, ctx):
        await ctx.send(file=File('discord.log', filename='log.txt'))



async def setup(bot):
    await bot.add_cog(Miscellaneous(bot))
