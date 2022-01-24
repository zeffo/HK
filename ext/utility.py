import json
import discord
from discord.ext import commands
import asyncio
import aiohttp
from io import BytesIO
from PIL import Image, ImageOps
import typing
import re
from concurrent.futures import ProcessPoolExecutor


def check():
    def pred(ctx):
        return ctx.author.id in (391847101228777482, 325616103143505932, 471635814745636875, 439377160940027911, 565624735451316235)
    return commands.check(pred)

class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot



    @commands.command()
    async def verify(self, ctx, _id: int):
        member = self.bot.get_guild(780294653450780682).get_member(_id)
        await member.add_roles(discord.Object(786013445794955314))
        await ctx.send(f'Verified {member.name}.', delete_after=3)

    @commands.command()
    @commands.is_owner()
    async def delete(self, ctx, m: discord.Message):
        try:
            await m.delete()
        except Exception as e:
            await ctx.send(e, delete_after=10)


    @commands.command()
    @commands.is_owner()
    async def ban(self, ctx, user: typing.Union[discord.Member, int]):
        if isinstance(user, discord.Member):
            if ctx.author.top_role <= user.top_role:
                return await ctx.send('You do not have sufficient permissions!', delete_after=5)
        await ctx.guild.ban(discord.Object(getattr(user, 'id', user)))

    @commands.command()
    @commands.is_owner()
    async def stfu(self, ctx, member: discord.Member, *args):
        args = args or ('deafen', 'mute')
        await member.edit(**{arg: True for arg in args})
        await ctx.send(f'Successfully gagged {member.name}!')

    
    @commands.command()
    @check()
    async def namaste(self, ctx, member: discord.Member, count=1):
        current = getattr(member.voice, 'channel', None)
        if count > 10:
            return await ctx.send('no')
        if not current:
            return await ctx.send('The ball must be in a voice channel to be boinged!')
        boings = 0
        for _ in range(count):
            tasks = [member.move_to(c) for c in ctx.guild.voice_channels]
            boings += len(tasks)
            await asyncio.gather(*tasks)
        await member.move_to(current)
        await ctx.send("boing\n"*boings)

    @commands.command()
    async def test(self, ctx):

        class DropDown(discord.ui.View):

            def __init__(self, options: list):
                super().__init__()
                item = discord.ui.Select(options=options)
                item.callback = self.callback
                self.add_item(item)
                self.menu = item

            async def callback(self, interaction):
                print(self.menu.values)

        
        view = DropDown([discord.SelectOption(label='test')])
        await ctx.send('test', view=view)


def setup(b):
    b.add_cog(Utility(b))