import logging
import traceback
from io import BytesIO, StringIO
from typing import Any

from discord import Embed, File, Interaction
from discord.app_commands.errors import AppCommandError, CommandNotFound
from discord.ext import commands

from ..bot import Bot
from ..music import MusicException
from ..protocols import GuildMessageable

logger = logging.getLogger("discord")


class Errors(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.hidden = True
        bot.tree.error(self.app_command_error)

    def send(self, interaction: Interaction):
        if interaction.response.is_done() and isinstance(
            interaction.channel, GuildMessageable
        ):
            return interaction.channel.send
        else:
            return interaction.response.send_message

    async def app_command_error(self, interaction: Interaction, error: AppCommandError):
        embed = None
        if isinstance(error, MusicException):
            embed = Embed(description=str(error))

        if embed is not None:
            embed.color = self.bot.conf.color
            return await self.send(interaction)(embed=embed)

        elif not isinstance(error, CommandNotFound):
            buffer = StringIO()
            traceback.print_exception(
                type(error), error, error.__traceback__, file=buffer
            )
            buffer.seek(0)
            buffer = BytesIO(buffer.getvalue().encode("utf-8"))
            if isinstance(interaction.channel, GuildMessageable):
                await self.send(interaction)(
                    "Observation: I seem to have ran into a problem.",
                    file=File(buffer, "traceback.txt"),
                )
                logger.error(buffer.getvalue())

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context[Any], error: Any):
        if not isinstance(error, commands.CommandNotFound):
            buffer = StringIO()
            traceback.print_exception(
                type(error), error, error.__traceback__, file=buffer
            )
            buffer.seek(0)
            buffer = BytesIO(buffer.getvalue().encode("utf-8"))
            await ctx.send(
                "Observation: I seem to have ran into a problem.",
                file=File(buffer, "traceback.txt"),
            )
            logger.error(buffer.getvalue())


async def setup(bot: Bot):
    await bot.add_cog(Errors(bot))
