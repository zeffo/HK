from discord.app_commands import AppCommandError

from .audio import *
from .queue import *
from .track import *
from .ytdl import *


class MusicException(AppCommandError):
    ...
