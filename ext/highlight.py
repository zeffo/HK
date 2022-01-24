import discord
from discord.ext import commands
import asyncio

# Highlight system, requested by bambinotbambi#5643

class Highlight(commands.Cog):
    '''A highlight system'''
    def __init__(self, bot):
        self.bot = bot

    async def get_keyword(self, keyword):
        async with self.bot.db.acquire() as con:
            result = await con.fetchrow('SELECT id FROM Highlights WHERE keyword=$1', keyword)
            if not result:
                await con.execute('INSERT INTO Highlights (keyword, count) VALUES ($1, 0)', keyword)
                result = await con.fetchrow('SELECT id FROM Highlights WHERE keyword=$1', keyword) 
            return result['id']

    @commands.group(invoke_without_command=True)
    async def highlight(self, ctx):
        await ctx.send('Subcommand not found!')

    @highlight.command()
    async def test(self, ctx, field, keyword):
        async with self.bot.db.acquire() as con:
            result = await con.fetchrow('SELECT $1 FROM Highlights WHERE keyword=$2', field, keyword)
            print(result)

    @highlight.command(usage='`hk highlight add (keyword)`')
    async def add(self, ctx, keyword):
        '''A command that adds the specifed keyword to the user's Highlights. The user will be DM'd when the highlighted word appears in a channel.'''
        keyword = keyword.lower()
        kwid = await self.get_keyword(keyword)
        async with self.bot.db.acquire() as con:
            await con.execute('INSERT INTO HighlightSubs (user_id, keyword_id) VALUES ($1, $2)', ctx.author.id, kwid)
            await ctx.send(f'Added {keyword} to your highlights!')

    @highlight.command(name='list', usage='`hk highlight list`')
    async def _list(self, ctx):
        '''A command that lists the Highlighted keywords of the user. '''
        async with self.bot.db.acquire() as con:
            ids = [r['keyword_id'] for r in (await con.fetch('SELECT keyword_id FROM HighlightSubs WHERE user_id=$1', ctx.author.id))]
            records = await con.fetch('SELECT keyword, count FROM Highlights WHERE id=ANY($1)', ids)
            await ctx.send(', '.join(f"{r['keyword']} ({r['count']})" for r in records) or 'You aren not highlighting anything yet.')
    
    @highlight.command(usage='`hk highlight remove`')
    async def remove(self, ctx, keyword):
        '''A command that removes the specified keyword from the user's highlights. '''
        keyword = keyword.lower()
        async with self.bot.db.acquire() as con:
            kwid = await con.fetchrow('SELECT id FROM Highlights WHERE keyword=$1', keyword)
            if not kwid:
                return await ctx.send('You do not have this keyword Highlighted.')
            records = await con.fetchrow('SELECT * FROM HighlightSubs WHERE user_id=$1 AND keyword_id=$2', ctx.author.id, kwid['id'])
            if records:
                await con.execute('DELETE FROM HighlightSubs WHERE user_id=$1 AND keyword_id=$2', ctx.author.id, kwid['id'])
                return await ctx.send(f'Removed {keyword} from your Highlights!')

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user or message.author.bot or not message.guild:
            return
        keywords = message.content.lower().split()
        async with self.bot.db.acquire() as con:
            data = await con.fetch('SELECT Highlights.keyword, HighlightSubs.user_id, Highlights.id FROM Highlights INNER JOIN HighlightSubs ON Highlights.id=HighlightSubs.keyword_id WHERE Highlights.keyword = ANY($1)', keywords)
        tasks = []
        for record in data:
            embed = discord.Embed(title='Highlight!', description=f'[{record["keyword"]}]({message.jump_url})', color=self.bot.color)
            async with self.bot.db.acquire() as con:
                await con.execute('UPDATE Highlights SET count = count + 1 WHERE id=$1', record['id'])
            embed.set_author(name=message.author.name, icon_url=str(message.author.avatar))
            user = self.bot.get_user(record['user_id'])
            if message.guild.get_member(user.id) and user != message.author:
                tasks.append(user.send(embed=embed))
        await asyncio.gather(*tasks)
        


def setup(bot):
    return
    bot.add_cog(Highlight(bot))