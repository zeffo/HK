from discord.ext import commands
import yt_dlp   # type: ignore

class MusicError(commands.CommandError):
    """Base exception for the music system"""

class DownloadError(yt_dlp.DownloadError):
    """Exception raised when a track failed to download"""