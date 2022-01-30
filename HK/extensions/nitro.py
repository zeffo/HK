import discord
from discord.ext import commands
from typing import Union\

class Nitro(commands.Cog):
    """ Fun commands to mimic nitro functionality! """
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(usage='`hk impersonate (User ID/mention) (content)`')
    @commands.bot_has_permissions(manage_webhooks=True)
    async def impersonate(self, ctx, target: Union[discord.Member, discord.User], *, message):
        ''' Command to send a message as another user via webhook '''
        wh = await ctx.channel.create_webhook(name=getattr(target, 'display_name', target.name), avatar=await target.avatar.read())
        await wh.send(message)
        await wh.delete()

def setup(bot):
    bot.add_cog(Nitro(bot))