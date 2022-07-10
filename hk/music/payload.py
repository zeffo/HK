from discord import Guild, Interaction, Member, VoiceClient

from ..bot import Bot
from ..protocols import GuildMessageable
from .errors import (
    DifferentVoiceChannelException,
    GuildOnlyException,
    NoVoiceChannelException,
)


class Payload:
    """Holds data required for most music functions"""

    def __init__(
        self,
        *,
        bot: Bot,
        guild: Guild,
        voice_client: VoiceClient,
        user: Member,
        channel: GuildMessageable,
        interaction: Interaction,
    ):
        self.bot = bot
        self.guild = guild
        self.voice_client = voice_client
        self.channel = channel
        self.user = user
        self.interaction = interaction

    @classmethod
    def validate(cls, bot: Bot, iact: Interaction):
        if (
            isinstance(iact.user, Member)
            and iact.guild is not None
            and isinstance(iact.channel, GuildMessageable)
        ):
            vstate, vclient = iact.user.voice, iact.guild.voice_client
            vc = vstate.channel if vstate else None
            if not vstate or not vc:
                raise NoVoiceChannelException
            if not isinstance(vclient, VoiceClient) or (vc and not vclient):
                raise DifferentVoiceChannelException(vc, None)
            if vc != vclient.channel:
                raise DifferentVoiceChannelException(vc, vclient.channel)
        else:
            raise GuildOnlyException

        return cls(
            bot=bot,
            guild=iact.guild,
            voice_client=vclient,
            user=iact.user,
            channel=iact.channel,
            interaction=iact,
        )

    @classmethod
    async def from_interaction(cls, bot: Bot, iact: Interaction):
        try:
            payload = cls.validate(bot, iact)
        except DifferentVoiceChannelException as e:
            if e.bot_vc is not None and len(e.bot_vc.members) == 1:
                if guild := iact.guild:
                    await guild.me.move_to(e.user_vc)
            else:
                await e.user_vc.connect()
            return cls.validate(bot, iact)

        return payload
