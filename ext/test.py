from discord.ext import commands


@commands.command()
async def lolo(ctx):
    await ctx.send("Works as intended!")


def setup(bot):
    for item in globals().values():
        if type(item) is commands.Command:
            bot.add_command(item)