from typing import Optional

from discord.app_commands import AppCommandError


class MusicException(AppCommandError):
    """Base exception for the music package"""

    message: Optional[str] = None

    def __str__(self):
        return str(self.message or self.__doc__)


class UnknownTrackException(MusicException):
    """Raised when the YouTube API is unable to return data"""

    message = "Couldn't find that track!"

    def __init__(self, query: str):
        self.query = query


class NoVoiceException(MusicException):
    """Raised when a guild's voice client is non-existent"""

    message = "You need to be in a voice channel!"


class GuildOnlyException(MusicException):
    """Raised when a command is used in a DM"""


class DifferentVoiceException(MusicException):
    """Raised when a user's voice channel is different from the bot's"""

    message = "You need to be in the same voice channel as the bot!"
