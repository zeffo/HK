from typing import Union

from discord import StageChannel, VoiceChannel
from discord.app_commands import AppCommandError


class MusicException(AppCommandError):
    """Base exception for the Music cog"""


UnknownTrackException = MusicException("Could not find that song!")
NoVoiceChannelException = MusicException("You must be in a voice channel!")

GuildOnlyException = MusicException("This command can only be used in a server!")


class DifferentVoiceChannelException(MusicException):
    """Raised when the user and bot are not in the same voice channel"""

    def __init__(
        self,
        user_vc: Union[VoiceChannel, StageChannel],
        bot_vc: Union[VoiceChannel, StageChannel, None],
    ):
        self.user_vc = user_vc
        self.bot_vc = bot_vc
