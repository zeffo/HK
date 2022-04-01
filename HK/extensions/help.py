from discord.ext import commands
from ..paginator import Unit, Paginator


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        bot.help_command = FormattedHelp()


class FormattedHelp(commands.HelpCommand):
    def __init__(self):
        super().__init__(command_attrs={"usage": "`hk help (command/category)`"})

    def get_usage(self, command):
        return f"hk {command.qualified_name} {' '.join([f'({arg})' for arg in command.clean_params])}"

    def get_cog_embed(self, cog):
        bot = self.context.bot
        embed = bot.embed(title=cog.qualified_name)
        if hasattr(cog, "description"):
            embed.description = cog.description
        return embed

    async def send_error_message(self, error):
        bot = self.context.bot
        embed = bot.embed(title=error)
        await self.get_destination().send(embed=embed)

    def get_command_embed(self, command):
        ctx = self.context
        embed = ctx.bot.embed(
            title=command.qualified_name,
            description=command.description,
            color=ctx.bot.color,
        )
        embed.add_field(name="Usage", value=self.get_usage(command))
        return embed

    def nsfw(self, command):
        return getattr(command, "nsfw", False) and not self.context.channel.is_nsfw()

    async def nsfw_warn(self):
        bot = self.context.bot
        await self.context.send(
            embed=bot.embed(
                title="You can only view NSFW commands in an NSFW channel!",
            ),
            delete_after=10,
        )

    async def send_command_help(self, command):
        if self.nsfw(command):
            return await self.nsfw_warn()
        if getattr(command, "hidden", False):
            return await self.send_error_message(
                self.command_not_found(command.qualified_name)
            )
        await self.context.send(embed=self.get_command_embed(command))

    async def send_cog_help(self, cog):
        if self.nsfw(cog):
            return await self.nsfw_warn()
        if getattr(cog, "hidden", False):
            return await self.send_error_message(
                self.command_not_found(cog.qualified_name)
            )
        units = [Unit(embed=self.get_cog_embed(cog))]
        for command in cog.walk_commands():
            units.append(Unit(embed=self.get_command_embed(command)))
        await self.context.send(
            embed=self.get_cog_embed(cog), view=Paginator(self.context, units=units)
        )

    async def send_group_help(self, group):
        if self.nsfw(group):
            return await self.nsfw_warn()
        if getattr(group, "hidden", False):
            return await self.send_error_message(
                self.command_not_found(group.qualified_name)
            )
        units = [Unit(embed=self.get_command_embed(group))]
        for command in group.walk_commands():
            units.append(Unit(embed=self.get_command_embed(command)))
        await self.context.send(
            embed=self.get_command_embed(group),
            view=Paginator(self.context, units=units),
        )

    async def send_bot_help(self, mapping):
        bot = self.context.bot
        start = bot.embed(
            title="HK-69 Commands",
            description="HK offers a plethora of commands for you to use!",
            color=self.context.bot.color,
        )
        start.set_image(
            url="https://cdn.discordapp.com/attachments/734363926208184320/862088250004865024/hk.jpg"
        )
        units = [Unit(embed=start)]
        mapping.pop(self.context.bot.get_cog("Help"))
        bot = self.context.bot
        for cog in mapping:
            if not getattr(cog, "hidden", False) and not self.nsfw(cog):
                embed = bot.embed(
                    title=cog.qualified_name if cog else "\u200b",
                    description="\n".join(
                        [
                            self.get_usage(command)
                            for command in mapping[cog]
                            if not getattr(command, "hidden", False)
                            and not self.nsfw(command)
                        ]
                    ),
                    color=self.context.bot.color,
                )
                if cog:
                    embed.description = f"{cog.description}\n\n{embed.description}"
                units.append(Unit(embed=embed))

        await self.context.send(embed=start, view=Paginator(self.context, units=units))


async def setup(b):
    await b.add_cog(Help(b))
