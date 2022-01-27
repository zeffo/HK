import typing
import discord
from discord.ext import commands
from discord.ext import ipc
import asyncio
from os import getenv, listdir
from dotenv import load_dotenv
from datetime import datetime
import asyncpg
import aiohttp
from subprocess import Popen, run
import sys


class Bot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def start(self):
        self.pool = await asyncpg.create_pool(getenv('DB_URI'))
        self.cs = aiohttp.ClientSession()

        for ext in listdir('ext'):
            if ext.endswith('.py'):
                bot.load_extension(f'ext.{ext[:-3]}')
                print(f'Loaded {ext}')
        for ext in other_exts:
            bot.load_extension(ext)
        await super().start(getenv('BOT_TOKEN'))



load_dotenv()
intents = discord.Intents.all()
bot = Bot(command_prefix=('♫', 'hk '), activity=discord.Game(name="Star Wars: The Old Republic"), intents=intents, allowed_mentions=discord.AllowedMentions(everyone=False))
bot.start_time = datetime.now()                             
bot.color = 0xa80000
bot.yt_key = getenv('YOUTUBE_API_KEY')
other_exts = ('jishaku',)
bot.super = lambda: commands.check(lambda ctx: ctx.author.id in [bot.owner_id, 391847101228777482])


@bot.command(aliases=['i', ])
async def invite(ctx):
    await ctx.send(embed=discord.Embed(description='[Invite me to your server!](https://discord.com/oauth2/authorize?client_id=716818354769362984&scope=bot&permissions=1073212631)\n`Created By Zeffo#9673. Very useless at the moment :D`'))

@bot.command(usage='`hk mnss`')
async def mnss(ctx):
    '''A command that sends my class timetable'''
    embed = discord.Embed()
    embed.set_image(url='https://cdn.discordapp.com/attachments/756100166825541733/829806414812938250/49780e73-d5fa-402d-bfd5-81499c71061b.png')
    await ctx.send(embed=embed)

@bot.command()
async def info(ctx):
    embed = discord.Embed(title='HK-69', description='Made by Zeffo#0393')
    await ctx.send(embed=embed)

@bot.command()
@commands.is_owner()
async def update(ctx):
    if __name__ == '__main__':
        await ctx.send("Preparing to update...")
        run(['git', 'pull', '-f', 'origin', 'master'])
        run([sys.executable, 'bot.py'])
        exit()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    bot.loop = loop
    try:
        loop.create_task(bot.start())
        loop.run_forever()
    except KeyboardInterrupt:
        loop.stop()
        print("Preparing to exit...")

    print("Finished.")