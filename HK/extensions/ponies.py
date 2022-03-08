from mylittlepony import Client
from discord.ext import commands
from discord import File
from random import choice
from HK.paginator import Paginator, Unit
from HK.__main__ import Bot
from io import StringIO

def wrap(s: str):
    return f"```md\n{s}\n```"

class MyLittlePony(commands.Cog):
    name = "My Little Pony"
    def __init__(self, bot: Bot):
        self.bot = bot
        self.client = Client()

    @classmethod
    async def connected(cls, bot):
        c = cls(bot)
        await c.client.connect()
        return c

    async def make_pony_embed(self, char):
        embed = self.bot.embed(title=f"{char.Name} {f'(aka {char.Alias})' if char.Alias else ''}", description=char.Url)
        if char.characters_images:
            image = await self.client.query.images.find_first(where={'ImageID': char.characters_images[0].ImageID})
            if image:
                embed.set_image(url=image.Url)
        for meta in ('Sex', 'Occupations', 'Residences'):
            content = wrap("\n".join([f"- {l}" for l in (getattr(char, meta, "-") or "-").split('\n')]))
            embed.add_field(name=meta, value=content, inline=False)
        
        return embed

    @commands.group(invoke_without_command=True)
    async def ponies(self, ctx):
        ret = await self.client.query.characters.find_many(include={'characters_images': True})
        units = []
        for char in ret:
            embed = await self.make_pony_embed(char)
            units.append(Unit(embed=embed))
        await ctx.send(embed=units[0].embed, view=Paginator(ctx, units=units))
        
    @ponies.command()
    async def find(self, ctx, *, name: str):
        name = name.title()
        pony = await self.client.query.characters.find_first(where={"Name": {'contains': name}}, include={'characters_images': True})
        if pony:
            embed = await self.make_pony_embed(pony)
            await ctx.send(embed=embed)
        else:
            await ctx.send("Observation: That Pony does not exist in my records.")

    @ponies.command()
    async def available(self, ctx):
        total = {c.Name for c in await self.client.query.characters.find_many()}
        current = {m.nick for m in ctx.guild.members}
        buffer = StringIO("- "+"\n- ".join(total-current))
        await ctx.send(file=File(buffer, "ponies.md"))

    @ponies.command()
    async def random(self, ctx):
        r = choice([c for c in await self.client.query.characters.find_many(include={'characters_images': True}) if c.Name not in {m.nick for m in ctx.guild.members}])
        await ctx.send(embed=await self.make_pony_embed(r))

async def wait_and_add(bot):
    cog = await MyLittlePony.connected(bot)
    bot.add_cog(cog)


def setup(bot):
    bot.loop.create_task(wait_and_add(bot))