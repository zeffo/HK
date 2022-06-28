from .ytdl import *
from .track import *
from .audio import *
from .queue import *

from discord.app_commands import AppCommandError


class MusicException(AppCommandError):
    ...
