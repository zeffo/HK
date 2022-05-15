from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from discord import Member, Message, VoiceProtocol
from discord.ext import commands

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

    async def send(self, *args: Any, **kwargs: Any) -> Message:
        if embed := kwargs.get('embed'):
            embed.color = self.bot.conf.color

        if embeds := kwargs.get('embeds'):
            for embed in embeds:
                embed.color = self.bot.conf.color

        return await super().send(*args, **kwargs)

