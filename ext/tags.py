import discord
from discord import message
from discord.ext import commands
from discord.ui import View, button
from typing import List
import asyncpg
from asyncio import Future

class Paginator(View):
    """Paginator for displaying `asyncpg.record.Record`"""

    EMOJIS = {
        'first': '<:first:861982503001653249>', 
        'next': '<:right:861982503266943018>', 
        'stop': '<:stop:861982503035600917>', 
        'back': '<:left:861982473420144643>', 
        'last': '<:last:861982503397228564>'
    }

    def __init__(self, messageable: discord.abc.Messageable, records: List[asyncpg.Record], *, chunk=25, owner=None):
        super().__init__()
        self.owner = owner
        self.destination = messageable
        self.records = records
        self.chunk = chunk
        self.message = Future()
        self.cursor = 0
        self.color = messageable.bot.color if isinstance(messageable, commands.Context) else 0xed8e00

    def chunks(self):
        i = 0
        for i in range(len(self.records)):
            yield self.records[i:i+self.chunk]
            i += self.chunk

    @property
    def embeds(self):
        ret = []
        for i, chunk in enumerate(self.chunks()):
            embed = discord.Embed(title=f"Page {i} of {len(self.records)//self.chunk}")
            embed.colour = self.color
            content = '\n'.join([r['keyword'] for r in chunk])
            embed.description = f"```\n{content}```"
            ret.append(embed)
        return ret or discord.Embed(title="404", description="No tags found :(", color=self.color)

    async def move(self, message, position: int):
        if position == self.cursor:
            return
        message = message or await self.message
        await message.edit(embed=self.embeds[position], view=self)
        
    async def create(self):
        message = await self.destination.send(embed=self.embeds[0], view=self)
        self.message.set_result(message)

    @button(emoji=EMOJIS['first'])
    async def first(self, button, interaction):
        await self.move(interaction.message, 0)
        self.cursor = 0

    @button(emoji=EMOJIS['back'])
    async def back(self, button, interaction):
        if self.cursor-1 == -1:
            return
        await self.move(interaction.message, self.cursor-1)
        self.cursor -= 1

    @button(emoji=EMOJIS['stop'])
    async def stop(self, button, interaction):
        await interaction.message.delete()

    @button(emoji=EMOJIS['next'])
    async def _next(self, button, interaction):
        if self.cursor + 1 == len(self.embeds):
            return
        await self.move(interaction.message, self.cursor+1)
        self.cursor += 1
    
    @button(emoji=EMOJIS['last'])
    async def last(self, button, interaction):
        pos = len(self.embeds) - 1
        await self.move(interaction.message, pos)
        self.cursor = pos

    async def interaction_check(self, interaction):
        if interaction.user == self.owner:
            return True
        else:
            await interaction.response.send_message("You cannot interact with someone else's command!", ephemeral=True) 

class Tags(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.pool: asyncpg.pool.Pool = bot.pool

    @commands.group(invoke_without_command=True)
    async def tag(self, ctx, *, name: str):
        async with self.pool.acquire() as con:
            result = await con.fetchrow("SELECT * FROM Tags WHERE keyword=$1", name)
        await ctx.send(result['meta'] if result else "Couldn't find that tag :(")

    @tag.command()
    async def create(self, ctx, keyword: str, *, meta: str):
        async with self.pool.acquire() as con:
            try:
                await con.execute('INSERT INTO Tags (keyword, meta) VALUES ($1, $2)', keyword, meta)
                reaction = "<:yes:866983565639942184>"
            except asyncpg.exceptions.UniqueViolationError:
                reaction = "❌"
            
        await ctx.message.add_reaction(reaction)
                

    @tag.command()
    async def delete(self, ctx, *, keyword: str):
        async with self.pool.acquire() as con:
            result = await con.execute('DELETE FROM Tags WHERE keyword=$1', keyword)
        await ctx.send(result)

    @tag.command()
    async def edit(self, ctx, keyword, *, meta):
        async with self.pool.acquire() as con:
            result = await con.execute('UPDATE Tags SET meta=$1 WHERE keyword=$2', meta, keyword)
        await ctx.send(result)

    @commands.command()
    async def tags(self, ctx):
        async with self.pool.acquire() as con:
            records = await con.fetch('SELECT keyword FROM Tags')
        paginator = Paginator(ctx, records, owner=ctx.author)
        await paginator.create()


def setup(bot):
    bot.add_cog(Tags(bot))