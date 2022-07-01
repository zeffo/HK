from discord import Guild, Interaction, Member, VoiceClient

from ..bot import Bot
from ..protocols import GuildMessageable
from .errors import (DifferentVoiceChannelException, MusicException,
                     NoVoiceChannelException)


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
        interaction: Interaction
    ):
        self.bot = bot
        self.guild = guild
        self.voice_client = voice_client
        self.channel = channel
        self.user = user
        self.interaction = interaction

    @classmethod
    async def from_interaction(cls, bot: Bot, iact: Interaction):
        try:
            assert (
                isinstance(iact.user, Member)
                and iact.guild is not None
                and isinstance(iact.channel, GuildMessageable)
            ), "This command can only be used in a server!"
            vstate, vclient = iact.user.voice, iact.guild.voice_client
            vc = vstate.channel if vstate else None
            if not vstate or not vc:
                raise NoVoiceChannelException
            if vc and not vclient:
                vclient = await vc.connect()
            assert isinstance(vclient, VoiceClient)
            if vclient and vc != vclient.channel:
                if len(vclient.channel.members) == 1:
                    await vclient.move_to(vc)
                else:
                    raise DifferentVoiceChannelException
        except AssertionError as e:
            raise MusicException(str(e))

        return cls(
            bot=bot,
            guild=iact.guild,
            voice_client=vclient,
            user=iact.user,
            channel=iact.channel,
            interaction=iact,
        )
