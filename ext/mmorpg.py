import discord
from discord.ext import commands


class SWTOR(commands.Cog):
    """ StarWars themed MMORPG in development!"""
    def __init__(self, bot):
        self.bot = bot




def setup(bot):
    bot.add_cog(SWTOR(bot))
