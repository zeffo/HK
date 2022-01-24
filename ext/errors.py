from discord.ext import commands


class Errors(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.hidden = True

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if ctx.command:
            if getattr(ctx.command, 'has_error_handler', lambda: 0)() or getattr(ctx.command.cog, 'cog_command_error', lambda: 0):
                return
        
        if not isinstance(error, commands.CommandNotFound):
            raise error


def setup(bot):
    bot.add_cog(Errors(bot))