import asyncpg
from discord.ext import commands
from ..paginator import Paginator, Unit
from ..__main__ import Bot
from ..utils import chunks

class Tags(commands.Cog):
    def __init__(self, bot):
        self.bot: Bot = bot
        self.pool: asyncpg.pool.Pool = bot.pool

    @commands.group(invoke_without_command=True)
    async def tag(self, ctx, *, name: str):
        """Retrieve and display a tag"""
        async with self.pool.acquire() as con:
            result = await con.fetchrow("SELECT * FROM Tags WHERE keyword=$1", name)
        await ctx.send(result['meta'] if result else "Couldn't find that tag :(")

    @tag.command()
    async def create(self, ctx, keyword: str, *, meta: str):
        """Create a tag"""
        async with self.pool.acquire() as con:
            try:
                await con.execute('INSERT INTO Tags (keyword, meta) VALUES ($1, $2)', keyword, meta)
                reaction = "<:yes:866983565639942184>"
            except asyncpg.exceptions.UniqueViolationError:
                reaction = "❌"
            
        await ctx.message.add_reaction(reaction)
                
    @tag.command()
    async def delete(self, ctx, *, keyword: str):
        """Delete a tag"""
        async with self.pool.acquire() as con:
            result = await con.execute('DELETE FROM Tags WHERE keyword=$1', keyword)
        await ctx.send(result)

    @tag.command()
    async def edit(self, ctx, keyword, *, meta):
        """Edit a tag's contents"""
        async with self.pool.acquire() as con:
            result = await con.execute('UPDATE Tags SET meta=$1 WHERE keyword=$2', meta, keyword)
        await ctx.send(result)

    @commands.command()
    async def tags(self, ctx):
        """List all tags"""
        async with self.pool.acquire() as con:
            records = await con.fetch('SELECT keyword FROM Tags')
        units = []
        for i, chunk in enumerate(chunks(records, 25)):  
            embed = self.bot.embed(title=f"Page {i+1} of {(len(records)//25)+1}")
            content = '\n'.join([r['keyword'] for r in chunk])
            embed.description = f"```\n{content}```"
            units.append(Unit(embed=embed))
        
        if units:
            await ctx.send(embed=units[0].embed, view=Paginator(ctx, units=units))
        else:
            await ctx.send(embed=self.bot.embed(title="404", description="Statement: No tags were found."))

def setup(bot):
    bot.add_cog(Tags(bot))