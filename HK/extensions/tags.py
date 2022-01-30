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
        await ctx.send(result["meta"] if result else "Couldn't find that tag :(")

    @tag.command()
    async def create(self, ctx, keyword: str, *, meta: str):
        """Create a tag"""
        async with self.pool.acquire() as con:
            try:
                await con.execute(
                    "INSERT INTO Tags (keyword, meta) VALUES ($1, $2)", keyword, meta
                )
                res = f"Statement: Tag {keyword} created successfully."
            except asyncpg.exceptions.UniqueViolationError:
                res = f"Observation: I cannot create that tag since it already exists."
        await ctx.send(res)

    @tag.command()
    async def delete(self, ctx, *, keyword: str):
        """Delete a tag"""
        async with self.pool.acquire() as con:
            result = await con.fetch("DELETE FROM Tags WHERE keyword=$1 RETURNING *;", keyword)
        await ctx.send(f"Statement: Deleted tag {keyword} successfully." if result else "Statement: Could not find that tag.")
    
    @tag.command()
    async def edit(self, ctx, keyword, *, meta):
        """Edit a tag's contents"""
        async with self.pool.acquire() as con:
            result = await con.execute(
                "UPDATE Tags SET meta=$1 WHERE keyword=$2 RETURNING *", meta, keyword
            )
        await ctx.send(f"Statement: Updated {keyword} successfully." if result else "Statement: Could not find that tag.")

    @commands.command()
    async def tags(self, ctx):
        """List all tags"""
        async with self.pool.acquire() as con:
            records = await con.fetch("SELECT keyword FROM Tags")
        if not records:
            return await ctx.send(
                embed=self.bot.embed(
                    title="404", description="Statement: No tags were found."
                )
            )
        units = []
        for i, chunk in enumerate(chunks(records, 10)):
            embed = self.bot.embed(title=f"Page {i+1} of {(len(records)//10)+1}")
            content = "\n".join([r["keyword"] for r in chunk])
            embed.description = f"```\n{content}```"
            units.append(Unit(embed=embed))
        await ctx.send(embed=units[0].embed, view=Paginator(ctx, units=units))


def setup(bot: Bot):
    if bot.pool:
        bot.add_cog(Tags(bot))
