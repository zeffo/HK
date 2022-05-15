from typing import Dict, List, Optional

import yaml
from pydantic import BaseModel


class Settings(BaseModel):
    color: int = 0xA80000
    emojis: Dict[str, str] = {
        "first": "⏮️",
        "stop": "⏹️",
        "last": "⏭️",
        "next": "➡️",
        "back": "⬅️",
    }
    prefix: str = "hk "
    intents: int = 131071
    extensions: List[str] = ["jishaku"]
    debug_guild: Optional[int]

    youtube_api_token: str
    discord_api_token: str
    postgres_uri: str
    application_id: int

    def __init__(self, fp: Optional[str]):
        fp = fp or "./settings.yaml"
        with open(fp) as f:
            super().__init__(**yaml.safe_load(f))
