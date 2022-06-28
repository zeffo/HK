from typing import List, Optional
from typing_extensions import TypedDict
from dotenv import load_dotenv
from os import environ
import yaml
from pydantic import BaseModel

__all__ = ("Config",)


class Emojis(TypedDict):
    forward: str
    stop: str
    skip: str
    next: str
    back: str
    playpause: str
    x: str


class EnvVars(TypedDict):
    YOUTUBE: str
    DISCORD: str
    DATABASE_URI: str


class Config(BaseModel):
    """Configuration settings"""

    color: int = 0xA80000
    emojis = Emojis(
        forward="⏮️", stop="⏹️", skip="⏭️", next="➡️", back="⬅️", playpause="⏯️", x="❌"
    )
    prefix: str = "hk "
    intents: int = 131071
    extensions: List[str] = ["jishaku"]
    debug_guilds: Optional[List[int]]
    env: EnvVars

    def __init__(self, fp: Optional[str] = None):
        load_dotenv()

        fp = fp or "./settings.yaml"
        with open(fp) as f:
            super().__init__(env=EnvVars(**dict(environ)), **yaml.safe_load(f))
