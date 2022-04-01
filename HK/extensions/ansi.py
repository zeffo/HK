import discord
from discord.ext import commands
import re


class ANSIstr(str):
    ESC = "\u001b"
    BASE = ESC + "[{format};{color}m"
    FORMATS = {"normal": 0, "bold": 1, "underline": 4}
    COLORS = {
        "black": 30,
        "red": 31,
        "green": 32,
        "yellow": 33,
        "blue": 34,
        "pink": 35,
        "cyan": 36,
        "white": 37,
    }
    temp = {}
    for color, value in COLORS.items():
        temp["bg" + color] = value + 10
        temp["br" + color] = value + 60
    COLORS.update(temp)
    del temp

    ALL = {}
    ALL.update(COLORS)
    ALL.update(FORMATS)

    def transform(self):
        if not (self[0] == "{" and self[-1] == "}"):
            return str(self)
        start = f"{self.ESC}["
        inner = self[1:-1].split()
        tokens = []
        for i in range(len(inner)):
            token = str(self.ALL.get(inner[i], "0"))
            tokens.append(token)
        start += ";".join(tokens) + "m"
        return start

    def split(self):
        tokens = (self.__class__(s.strip()) for s in re.split(r" ?({.*?})", self))
        return [t for t in tokens if t]


class ANSIBuilder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(invoke_without_command=True)
    async def ansi(self, ctx):
        await ctx.send(
            f"Formats: {', '.join(ANSIstr.FORMATS)}, Colors: {', '.join(ANSIstr.COLORS)}"
        )

    @ansi.command()
    async def escape(self, ctx):
        await ctx.send(f"`{ANSIstr.ESC}`")

    def prepare(self, content):
        content = ANSIstr(content.strip("```").lstrip("ansi")).split()
        content = [s.transform() for s in content]
        return content

    @ansi.command()
    async def format(self, ctx, *, content):
        content = self.prepare(content)
        await ctx.send(f"```ansi\n{''.join(content)}\n```")

    @ansi.command()
    async def raw(self, ctx, *, content):
        content = self.prepare(content)
        await ctx.send(f"```\n{''.join(content)}\n```")


async def setup(bot):
    await bot.add_cog(ANSIBuilder(bot))
