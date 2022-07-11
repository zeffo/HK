from discord.app_commands import AppCommandError


class MusicException(AppCommandError):
    """Base exception for the music package"""


class UnknownTrackException(MusicException):
    """Raised when the YouTube API is unable to return data"""

    def __init__(self, query: str):
        self.query = query

    def __str__(self):
        return f"{self.__class__.__name__}: {self.query}"


class NoVoiceException(MusicException):
    """Raised when a guild's voice client is non-existent"""


class GuildOnlyException(MusicException):
    """Raised when a command is used in a DM"""
