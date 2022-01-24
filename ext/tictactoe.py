from discord.interactions import Interaction
from discord.ui import View, button, Button
from discord import Member, ButtonStyle
from discord.ext import commands
from random import shuffle
import asyncio


class Match:
    def __init__(self, p1, p2):
        self.board = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
        self.players = [p1, p2]
        shuffle(self.players)   # To randomise turn order
        self.X, self.O = self.players
        self.values = {self.X: 1, self.O: -1}
        self._turns = 0
    
    @property
    def turn(self):
        return self.players[0]
    
    def move(self, player, x, y):
        if not self.board[y][x] and player == self.turn:   
            self.board[y][x] = self.values[player]
        print(self.values[player], self.board)
        self.players = self.players[::-1]
        wins = []
        for row in self.board:
            wins.append(self._check(row))
        
        for column in [[row[i] for i in range(3)] for row in self.board]:
            wins.append(self._check(column))
        
        wins.append(self._check([self.board[x][x] for x in range(3)]))
        wins.append(self._check([self.board[2-x][x] for x in range(3)]))

        self._turns += 1

        for win in wins:
            if win:
                return win.name

        if self._turns == 9:
            return "Draw! No one "
        

    def _check(self, items):
        valid = {v*3: k for k, v in self.values.items()}
        print(items, sum(items))
        return valid.get(sum(items), False)


class Slot(Button):

    def __init__(self, row: int, col: int):
        self.row = row
        self.col = col
        self.coords = (col, row)
        super().__init__(style=ButtonStyle.blurple, label="\u200b", row=row)
    
    async def callback(self, interaction):
        await self.view.move(self, interaction)

class TicTacToeView(View):
    def __init__(self, ctx, p2):
        super().__init__()
        self.ctx = ctx
        self.p1 = ctx.author
        self.p2 = p2
        self.match = Match(self.p1, self.p2)

        for y in range(3):
            for x in range(3):
                self.add_item(Slot(x, y))
    
    async def move(self, button, interaction: Interaction):
        col, row = button.coords
        if interaction.user == self.match.turn and self.match.board[col][row] == 0:
            button.label = 'X' if self.match.values[interaction.user] == 1 else "O"
            await interaction.response.edit_message(view=self)
            if w := self.match.move(interaction.user, row, col):
                await interaction.edit_original_message(content=f"{w} wins!")
                self.stop()
        else:
            return await interaction.response.send_message("You cannot do this!", ephemeral=True)

        
class TicTacToe(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command()
    async def tictactoe(self, ctx, p2: Member):
        confirmation = await ctx.send(f'{p2.name}, send "accept" to start! _(Expires in 30 seconds)_')
        try:
            await self.bot.wait_for('message', check=lambda m: m.author.id == p2.id and m.content.lower() == 'accept', timeout=30.0)
        except asyncio.TimeoutError:
            return await confirmation.delete()
        view =  TicTacToeView(ctx, p2)
        await ctx.send(f"{view.match.turn.name} goes first!", view=view)


def setup(bot):
    bot.add_cog(TicTacToe(bot))