from discord import VoiceChannel
from discord.ext.commands import Context, Bot  # type: ignore
from discord import VoiceProtocol, VoiceChannel, StageChannel, Member
from typing import Optional, Union


class Context(Context[Bot]):
    async def connect(
        self,
    ) -> Optional[Union[VoiceProtocol, VoiceChannel, StageChannel]]:
        """Return the current voice client, or attempt to join the author's voice channel."""
        if self.voice_client is not None and getattr(
            self.voice_client, "channel", None
        ):
            return self.voice_client
        elif isinstance(self.author, Member) and self.author.voice:
            if vc := self.author.voice.channel:
                return await vc.connect()
