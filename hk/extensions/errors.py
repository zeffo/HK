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

    async def app_command_error(self, interaction: Interaction, error: AppCommandError):
        embed = None
        if isinstance(error, MusicException):
            embed = Embed(description=error)
        if embed:
            embed.color = self.bot.conf.color
            if not interaction.response.is_done():
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send(embed=embed)

        elif not isinstance(error, CommandNotFound):
            buffer = StringIO()
            traceback.print_exception(
                type(error), error, error.__traceback__, file=buffer
            )
            buffer.seek(0)
            buffer = BytesIO(buffer.getvalue().encode("utf-8"))
            if isinstance(interaction.channel, GuildMessageable):
                send = (
                    interaction.response.send_message
                    if not interaction.response.is_done()
                    else interaction.channel.send
                )
                await send(
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
