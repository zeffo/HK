from __future__ import annotations
from discord.ext import commands
from discord import VoiceProtocol, Member
from typing import Optional, TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .bot import Bot
 

class Context(commands.Context['Bot']):
    skip: bool = False
    
    async def connect(
        self,
    ) -> Optional[VoiceProtocol]:
        """Return the current voice client, or attempt to join the author's voice channel."""
        if self.voice_client is not None and getattr(
            self.voice_client, "channel", None
        ):
            return self.voice_client
        elif isinstance(self.author, Member) and self.author.voice:
            if vc := self.author.voice.channel:
                return await vc.connect()

    async def send(self, *args: Any, **kwargs: Any):
        if embed := kwargs.get('embed'):
            embed.color = self.bot.conf.color

        if embeds := kwargs.get('embeds'):
            for embed in embeds:
                embed.color = self.bot.conf.color

        await super().send(*args, **kwargs)

