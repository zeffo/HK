import discord
from discord.ext import commands
import random
from concurrent.futures import ProcessPoolExecutor


class Wholesome(commands.Cog):
    """ Commands that will warm your heart. """
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def hug(self, ctx, user: discord.User):
        embed = discord.Embed(title='<3', color=self.bot.color)
        GIFS = ('https://media.tenor.com/images/4294deb5ec97086243174b085d609695/tenor.gif', 'https://media1.tenor.com/images/2d4138c7c24d21b9d17f66a54ee7ea03/tenor.gif?itemid=12535134', 'https://media1.tenor.com/images/1a546758d4a88f2ed56ea2a9afa48f00/tenor.gif?itemid=16430376')
        embed.set_image(url=random.choice(GIFS))
        embed.set_footer(text=f'{user.name}, have a hug from {ctx.author.name} and have a lovely day! <3')
        await ctx.send(embed=embed)

    @hug.error
    async def hug_error(self, ctx, error):
        if isinstance(error, commands.errors.UserNotFound):
            await ctx.send('Ping the person you want to hug!', delete_after=3)
        else:
            raise error


def setup(bot):
    bot.add_cog(Wholesome(bot))