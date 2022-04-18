from discord.ext import commands
from discord import File, Member, Embed
from typing import TYPE_CHECKING
from aiohttp import ClientSession

if TYPE_CHECKING:
    from ..__main__ import Bot


class Action:
    name: str
    url: str

    async def get_data(self, session):
        resp = await session.get(self.url)
        return await resp.json()

    async def get_url(self):
        raise NotImplementedError

    async def embed(self, ctx, target):
        embed = Embed(title=f"{ctx.author.name}, you {self.name}ed {target.name}!")
        embed.set_image(url=await self.get_url(ctx))
        embed.color = ctx.bot.color
        return embed

class Hug(Action):
    name = "hugg"
    url = "https://some-random-api.ml/animu/hug"
    async def get_url(self, ctx):
        resp = await self.get_data(ctx.bot._session)
        return resp["link"] 

class Kiss(Action):
    name = "kiss"
    url = "https://neko-love.xyz/api/v1/kiss"
    async def get_url(self, ctx):
        resp = await self.get_data(ctx.bot._session)
        return resp["url"] 

class Punch(Action):
    name = "punch"
    url = "https://neko-love.xyz/api/v1/punch"
    async def get_url(self, ctx):
        resp = await self.get_data(ctx.bot._session)
        return resp["url"] 


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

    def create_embed(self, url, action, author, target):
        embed = Embed(title=f"{author.name}, you {action}ed {target.name}!")
        embed.set_image(url=url)
        embed.color = self.bot.color
        return embed

    @commands.command()
    async def hug(self, ctx, target: Member):
        await ctx.send(embed=await Hug().embed(ctx, target))

    @commands.command()
    async def kiss(self, ctx, target: Member):
        await ctx.send(embed=await Kiss().embed(ctx, target))

    @commands.command()
    async def punch(self, ctx, target: Member):
        await ctx.send(embed=await Punch().embed(ctx, target))



async def setup(bot):
    await bot.add_cog(Miscellaneous(bot))
