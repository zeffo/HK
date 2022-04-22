from asyncio.tasks import ALL_COMPLETED
from io import BytesIO
from discord import Embed, File, SelectOption
from discord.ext import commands
from discord.ui import View, button, select
from PIL import Image, ImageFont, ImageDraw
from asyncio import get_running_loop, wait
from wonderwords import RandomWord
from textwrap import wrap
from datetime import datetime, timezone

class Game(View):
    LEVELS = {'easy': 3, 'medium': 5, 'hard': 8, 'extreme': 12}
    def __init__(self, ctx):
        super().__init__(timeout=300)
        self.ctx = ctx
        self.players = {ctx.author}
        self.level = 5

    @button(label='Join')
    async def join(self, interaction, button):
        self.players.add(interaction.user)
        embed = Embed(title="TypeRacer", color=self.ctx.bot.color)
        desc = "\n".join([player.name for player in self.players])
        embed.description = f"```md\n{desc}\n```"
        await interaction.response.edit_message(embed=embed)

    @button(label='Start')
    async def start(self, interaction, button):
        if interaction.user != self.ctx.author:
            return
        await interaction.response.defer()
        file = await self.generate()
        start = await interaction.followup.send(file=file)
        started = start.created_at
        coros = []
        for player in self.players:
            check = lambda p: lambda m: m.author == p and m.channel == self.ctx.channel
            coros.append(self.ctx.bot.wait_for('message', check=check(player)))
        responses, _ = await wait(coros, return_when=ALL_COMPLETED)
        results = []
        embed = Embed(title="Results", description="```md\n")
        for _resp in responses:
            resp = await _resp
            score = 0
            for correct, ans in zip(self.words, resp.content.split()):
                if correct.strip() == ans.strip():
                    score += 1
            time = (resp.created_at-started).total_seconds()
            res = round(score - (time/(self.level/2)), 2)
            wpm = round((len(resp.content)/time)*12, 2)
            acc = round((score/len(self.words))*100, 2)
            results.append((resp.author, res, wpm, acc, time))
            
        desc = "\n".join(f"{i+1}. {player.name}: {score} | WPM: {wpm} | Time: {time}s | Accuracy: {acc}" for i, (player, score, wpm, acc, time) in enumerate(sorted(results, key=lambda t: t[1], reverse=True)))
        embed.description = f"```md\n{desc}\n```"
        await interaction.followup.send(embed=embed)

    @select(placeholder="Choose Difficulty: ", options=[SelectOption(label=x.title(), value=x) for x in LEVELS])
    async def difficulty(self, interaction, selectrow):
        if interaction.user != self.ctx.author:
            return
        await interaction.response.defer()
        items = selectrow.values
        if items:
            self.level = self.LEVELS[items[0]]

    def _generate_image(self):
        self.words = RandomWord().random_words(15, word_min_length=self.level-2, word_max_length=self.level+2)
        self.chars = " ".join(self.words)
        self.text = "\n".join(wrap(self.chars, width=30, break_on_hyphens=False))
        base = Image.new(mode='RGBA', size=(800, 400), color=(255, 0, 0, 0))
        small = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 43, )
        canvas = ImageDraw.Draw(base)
        canvas.multiline_text((10, 10), self.text, font=small, fill=(255, 255, 255), spacing=10.0, stroke_fill=(0, 0, 0), stroke_width=2)
        buffer = BytesIO()
        base.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer
        
    async def generate(self) -> File:
        image = await get_running_loop().run_in_executor(None, self._generate_image)
        return File(image, filename='words.png')


class TypeRacer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.group(invoke_without_command=True)
    async def typeracer(self, ctx):
        pass

    @typeracer.command()
    async def play(self, ctx):
        embed = Embed(title="TypeRacer", color=ctx.bot.color)
        embed.description = f"```md\n{ctx.author.name}\n```"
        await ctx.send(embed=embed, view=Game(ctx))

        
async def setup(b):
    await b.add_cog(TypeRacer(b))