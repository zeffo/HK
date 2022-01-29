import traceback
import discord
import logging
from io import StringIO
from discord.ext import commands

logger = logging.getLogger('discord')

class Errors(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.hidden = True

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if ctx.command:
            if getattr(ctx.command, "has_error_handler", lambda: 0)() or getattr(
                ctx.command.cog, "cog_command_error", 0
            ):
                return

        if not isinstance(error, commands.CommandNotFound):
            buffer = StringIO()
            traceback.print_exception(type(error), error, error.__traceback__, file=buffer)
            await ctx.send("Observation: I seem to have ran into a problem.", file=discord.File(buffer, 'traceback.txt'))
            logger.error(buffer.getvalue())


def setup(bot):
    bot.add_cog(Errors(bot))
