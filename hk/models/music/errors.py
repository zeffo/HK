import yt_dlp  # type: ignore
from discord.ext import commands


class MusicError(commands.CommandError):
    """Base exception for the music system"""

class DownloadError(yt_dlp.DownloadError):
    """Exception raised when a track failed to download"""
