import discord
from discord.ext import commands
from subprocess import Popen
import sys

class Update(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def update(self):
        Popen(['git', 'pull', 'master'])
        Popen([sys.executable, 'bot.py'])




def setup(bot):
    bot.add_cog(Update(bot))