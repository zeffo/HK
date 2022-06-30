from discord.app_commands import AppCommandError


class MusicException(AppCommandError):
    """Base exception for the Music cog"""


UnknownTrackException = MusicException("Could not find that song!")
NoVoiceChannelException = MusicException("You must be in a voice channel!")
DifferentVoiceChannelException = MusicException(
    "You must be in the same voice channel as the bot!"
)
GuildOnlyException = MusicException("This command can only be used in a server!")
