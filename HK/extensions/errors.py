import traceback
import discord
import logging
from io import StringIO
from discord.ext import commands

logger = logging.getLogger("discord")


class Errors(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.hidden = True

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if ctx.command:
            if ctx.command.has_error_handler() or ctx.command.cog.has_error_handler():
                return
        if isinstance(error, commands.NotOwner):
            await ctx.send("Statement: Only the bot owner may use this command!", delete_after=10)

        elif not isinstance(error, commands.CommandNotFound):   
            buffer = StringIO()
            traceback.print_exception(
                type(error), error, error.__traceback__, file=buffer
            )
            buffer.seek(0)
            await ctx.send(
                "Observation: I seem to have ran into a problem.",
                file=discord.File(buffer, "traceback.txt"),
            )
            logger.error(buffer.getvalue())


def setup(bot):
    bot.add_cog(Errors(bot))
