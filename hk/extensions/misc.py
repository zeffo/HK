from typing import ClassVar, Protocol, Union

from aiohttp import ClientSession
from discord import Embed, Interaction, Member, User, app_commands
from discord.ext import commands

from ..bot import Bot


class Action(Protocol):
    name: ClassVar[str]
    url: ClassVar[str]

    @classmethod
    async def get_data(cls, session: ClientSession):
        resp = await session.get(cls.url)
        return await resp.json()

    @classmethod
    async def get_url(cls, session: ClientSession) -> str:
        raise NotImplementedError

    @classmethod
    async def embed(
        cls, bot: Bot, interaction: Interaction, target: Union[User, Member]
    ):
        embed = Embed(
            description=f"{interaction.user.name} {cls.name}ed {target.name}!"
        )
        embed.set_image(url=await cls.get_url(bot.session))
        embed.color = bot.conf.color
        return embed


class Hug(Action):
    name = "hugg"
    url = "https://some-random-api.ml/animu/hug"

    @classmethod
    async def get_url(cls, session: ClientSession):
        resp = await cls.get_data(session)
        return resp["link"]


class Kiss(Action):
    name = "kiss"
    url = "https://neko-love.xyz/api/v1/kiss"

    @classmethod
    async def get_url(cls, session: ClientSession):
        resp = await cls.get_data(session)
        return resp["url"]


class Punch(Action):
    name = "punch"
    url = "https://neko-love.xyz/api/v1/punch"

    @classmethod
    async def get_url(cls, session: ClientSession):
        resp = await cls.get_data(session)
        return resp["url"]


class Miscellaneous(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        actions = Kiss, Punch, Hug

        def callback(act: Action):
            async def inner(interaction: Interaction, target: Member):
                await interaction.response.send_message(
                    embed=await act.embed(bot, interaction, target)
                )

            return inner

        for act in actions:
            cm = app_commands.ContextMenu(name=act.__name__, callback=callback(act))
            self.bot.tree.add_command(cm)


async def setup(bot: Bot):
    await bot.add_cog(Miscellaneous(bot))
