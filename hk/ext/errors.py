import logging
import traceback
from io import BytesIO, StringIO

from discord import File, Interaction
from discord.app_commands.errors import AppCommandError, CommandNotFound
from discord.ext import commands

from ..models.bot import Bot
from ..models.context import Context

logger = logging.getLogger("discord")


class Errors(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.hidden = True
        bot.tree.error(self.app_command_error)

    async def app_command_error(self, interaction: Interaction, error: AppCommandError):
        if not isinstance(error, CommandNotFound):
            raise error

    @commands.Cog.listener()
    async def on_command_error(self, ctx: Context, error: Exception):
        if ctx.command and not ctx.skip:    
            if ctx.command.has_error_handler():
                return
            if cog := ctx.command.cog:
                if cog.has_error_handler():
                    return
        if isinstance(error, commands.NotOwner):
            await ctx.send(
                "Statement: Only the bot owner may use this command!", delete_after=10
            )

        elif isinstance(error, commands.BadArgument):
            await ctx.send(
                embed=f"I wasn't able to parse the command! Please make sure all the arguments are correct."
            )

        elif not isinstance(error, commands.CommandNotFound):
            buffer = StringIO()
            traceback.print_exception(
                type(error), error, error.__traceback__, file=buffer
            )
            buffer.seek(0)
            buffer = BytesIO(buffer.getvalue().encode('utf-8'))
            await ctx.send(
                "Observation: I seem to have ran into a problem.",
                file=File(buffer, "traceback.txt"),
            )
            logger.error(buffer.getvalue())


async def setup(bot: Bot):
   await bot.add_cog(Errors(bot))
