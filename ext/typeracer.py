from asyncio.tasks import ALL_COMPLETED
from collections import defaultdict
from io import BytesIO
from discord import Embed, File
from discord.ext import commands
from discord.ui import View, button
from PIL import Image, ImageFont, ImageDraw
from functools import wraps, partial
from asyncio import Future, get_running_loop, wait, gather, sleep
from wonderwords import RandomWord
from textwrap import wrap
from datetime import datetime


class TextImageGenerator:
    def __init__(self, maxwords=15, *, difficulty):
        self.maxwords = maxwords
        difficulties = {'easy': 3, 'medium': 5, 'hard': 8, 'extreme': 12}
        length = difficulties[difficulty]
        words = RandomWord().random_words(maxwords, word_min_length=length-2, word_max_length=length+2)
        self.text = "\n".join(wrap(" ".join(set(words)), width=30, break_on_hyphens=False))
    
    def thread(func):
        """ Runs a function in another thread, returns a Future """
        @wraps(func)
        def wrapper(*args, **kwargs) -> Future:
            return get_running_loop().run_in_executor(None, partial(func, *args, **kwargs))
        return wrapper

    @thread
    def _generate_image(self):
        base = Image.new(mode='RGBA', size=(800, 400), color=(255, 0, 0, 0))
        small = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 43, )
        canvas = ImageDraw.Draw(base)
        canvas.multiline_text((10, 10), self.text, font=small, fill=(255, 255, 255), spacing=10.0, stroke_fill=(0, 0, 0), stroke_width=2)
        buffer = BytesIO()
        base.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer
        
    async def generate(self) -> File:
        image = await self._generate_image()
        return File(image, filename='words.png')


class SinglePlayerView(View):
    def __init__(self, ctx, difficulty):
        self.difficulty = difficulty
        self.ctx = ctx
        super().__init__()

    async def interaction_check(self, interaction):
        return interaction.user == self.ctx.author
    
    @button(label='Start')
    async def ready(self, button, interaction):
        await interaction.response.defer()
        gen = TextImageGenerator(difficulty=self.difficulty)
        image = await gen.generate()
        await interaction.followup.send("Start typing!", file=image)
        started = datetime.utcnow()
        message = await self.ctx.bot.wait_for('message', check=lambda m: m.author==self.ctx.author and m.channel==self.ctx.channel)
        ended = datetime.utcnow()
        time = ended - started
        words = gen.text.split()
        total = set(words)
        correct = set()
        for base, word in zip(message.content.split(), words):
            if base.strip() == word.strip():
                correct.add(word)
        
        perc = (len(correct)/len(words))*100
        cps = len(message.content)/time.total_seconds()
        embed = Embed(title="TypeRacer", description=f"Accuracy: {perc}%\nTime: {time}\nCPS: {cps}", color=self.ctx.bot.color)
        embed.add_field(name="Incorrect Words", value=", ".join(total-correct))
        embed.set_footer(text="CPS stands for Characters per Second. We do not use useless and misleading metrics like 'WPM'.")
        await interaction.channel.send(embed=embed)
        self.stop()


class MultiPlayerView(View):
    def __init__(self, ctx, difficulty):
        super().__init__()
        self.difficulty = difficulty
        self.ctx = ctx
        self.players = [ctx.author]

    @button(label="Join")
    async def join(self, button, interaction):
        if len(self.players) < 25:
            if interaction.user not in self.players:
                self.players.append(interaction.user)
                players = '\n- '.join(map(str, self.players))
                await interaction.response.edit_message(content=f"```md\n- {players}```")
            else:
                await interaction.response.send_message("You are already in this lobby!", ephemeral=True)
        else:
            await interaction.response.send_message("The Match is full!", ephemeral=True)
    
    @button(label="Start")
    async def start(self, button, interaction):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("You cannot do this!", ephemeral=True)
        await interaction.response.defer()
        gen = TextImageGenerator(difficulty=self.difficulty)
        image = await gen.generate()
        await interaction.followup.send("Start typing!", file=image)
        started = datetime.utcnow() 

        coros = []
        for player in self.players:
            check = lambda p: lambda m: m.author == p and m.channel == self.ctx.channel
            coros.append(self.ctx.bot.wait_for('message', check=check(player)))

        responses, _ = await wait(coros, return_when=ALL_COMPLETED)
        words = gen.text.split()
        results = defaultdict(list)
        for response in responses:
            response = await response
            correct = 0
            for base, word in zip(response.content.split(), words):
                if base.strip() == word.strip():
                    correct += 1
            incorrect = len(words) - correct
            time = response.created_at.replace(tzinfo=None) - started
            perc = (correct/len(gen.text.split()))*100
            cps = len(response.content)/time.total_seconds()
            data = {'player': response.author, 'cps': cps, 'perc': perc, 'time': time, 'correct': correct, 'incorrect': incorrect}
            results[correct].append(data)

        top = []
        for correct, players in sorted(results.items(), reverse=True):
            if len(top) >= 25:
                break
            top.extend(sorted(players, key=lambda d: d['time']))

        embed = Embed(title="Results", color=self.ctx.bot.color)
        for i, result in enumerate(top[:25]):
            embed.add_field(name=f"{i+1}. {result['player'].name}", value=f"CPS: {round(result['cps'], 2)}, Accuracy: {round(result['perc'], 2)}%, Time: {result['time'].total_seconds()}s")
        await self.ctx.send(embed=embed)

        
class PrivateView(View):
    """For private (custom) matches"""


class GetModeView(View):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self.result = None

    async def interaction_check(self, interaction):
        return interaction.user == self.ctx.author
    
    @button(label='Singleplayer')
    async def sp(self, button, interaction):
        self.result = SinglePlayerView
        self.stop()

    @button(label='Multiplayer')
    async def mp(self, button, interaction):
        self.result = MultiPlayerView
        self.stop()


class TypeRacer(commands.Cog):

    modes = {'singleplayer': SinglePlayerView}
    
    def __init__(self, bot):
        self.bot = bot
        self.sessions = {}

    async def get_mode(self, ctx):
        view = GetModeView(ctx)
        await ctx.send("Select gamemode: ", view=view)
        await view.wait()
        return view.result
    
    @commands.command()
    async def typeracer(self, ctx, difficulty="easy"):
        mode = await self.get_mode(ctx)
        view = mode(ctx, difficulty=difficulty)
        content = "TypeRacer Singleplayer"
        if isinstance(view, MultiPlayerView):
            content = f"TypeRacer Multiplayer\n```md\nPlayers:\n- {ctx.author.name}\n```"
        await ctx.send(content, view=view)


def setup(bot):
    bot.add_cog(TypeRacer(bot))