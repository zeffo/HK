from discord import Message, Member, User, ClientUser, PartialEmoji, File, Color
from discord.components import SelectOption
from discord.embeds import Embed
from discord.enums import ButtonStyle
from discord.ui import View, button, select
from discord.errors import Forbidden, HTTPException, NotFound
from discord.ext import commands, flags
from typing import List, Union, Optional, Tuple
from PIL import Image, ImageOps, ImageChops, UnidentifiedImageError, ImageFilter, ImageEnhance
from io import BytesIO
from PyPDF2 import PdfFileMerger, PdfFileReader
from asyncio import get_running_loop, AbstractEventLoop, Future
from functools import wraps, partial
from discord.ext.commands.errors import ArgumentParsingError, BadColourArgument
from concurrent.futures import ProcessPoolExecutor
import pyqrcode


class URL(commands.Converter):
    """ Returns a BytesIO object from a URL """
    async def convert(self, ctx, arg):
        try:
            ret = await ctx.bot.http.get_from_cdn(arg)
            return ret
        except (NotFound, Forbidden, HTTPException):
            return None

# These classes represent the common sources an image can be retrieved from. `None` is present in the case an invalid source is provided. 
MODELS = Union[Message, Member, URL, User, PartialEmoji, None]
class Targets:
    """ This class helps identify targets from which an image can be retrieved. """

    def __init__(self, ctx: commands.Context):
        self.ctx = ctx
        self.priority: Tuple = (self.attachments, self.parameters, self.reference, self.authors) # Functions listed here must return a sequence of BytesIO, preferably tuple or list

    async def targets(self, size=None) -> List[BytesIO]:
        """ Returns a list of BytesIO objects from the priority list (`Targets.priority`) """
        found = []
        count = 0
        for method in self.priority:
            res = await method()
            found += res
            count += len(res)
            if size:
                if len(found) >= size:
                    return found[:size]
        return found

    async def from_any(self, target):
        if isinstance(target, Message):
            if not target.attachments:
                raise NoTarget("Message has no attachments!")
            _bytes = await target.attachments[0].read()
        elif isinstance(target, (User, ClientUser, Member)):
            _bytes = await target.avatar.read()
        elif isinstance(target, bytes):
            _bytes = target
        elif isinstance(target, PartialEmoji):
            _bytes = await target.url.read()
        else:
            _bytes = None
        return BytesIO(_bytes) if _bytes else None

    async def attachments(self) -> List[BytesIO]:
        """ Return a List of BytesIO objects from the original message's attachments. """
        return [BytesIO(await att.read()) for att in self.ctx.message.attachments]

    async def parameters(self) -> List[BytesIO]:
        """ Return a List of BytesIO objects from the command parameters. """
        args = self.ctx.args
        if not args:
            return []
        if isinstance(args[0], commands.Cog):
            args.pop(0)
        args.pop(0)
        parameters = args + list(self.ctx.kwargs.values())
        ret = []
        for param in parameters:
            res = await self.from_any(param)
            if res:
                ret.append(res)
        return ret

    async def reference(self) -> List[BytesIO]:
        """ Return a List of BytesIO objects from the reference message's attachments."""
        return [BytesIO(await att.read()) for att in self.ctx.message.reference.resolved.attachments] if self.ctx.message.reference else []
    
    async def authors(self) -> List[BytesIO]:
        """ Returns a List of BytesIO objects from the avatars of the authors of the original message and the referenced message. """
        targets = []
        if self.ctx.message.reference:
            targets.append(self.ctx.message.reference.resolved.author)
        targets.append(self.ctx.author)
        return [BytesIO(await m.avatar.read()) for m in targets]

class NoTarget(Exception):
    """ Raised when an invalid target is passed."""

    def __init__(self, reason):
        self.reason = reason

    def __str__(self):
        return f"Invalid target: {self.reason}!"


class Machine:
    """
    This class provides methods for image modification.

    Please ensure that blocking I/O is run in a thread. A decorator `Machine.thread` is provided for this.
    Another decorator, `Machine.targets` is provided to ensure that the number of targets required for the operation are present.

    Image modification commands should be used for a variety of sources, such as message attachments, profile pictures, and custom emojis. To make retrieving the target bytes easier, a classmethod `Machine.from_discord` has been provided.
    Another classmethod, `Machine.from_command` has been provided to help make command-making easier.
    """

    def __init__(self, *sources, loop=Optional[AbstractEventLoop]):
        self.sources = list(sources)
        try:
            self.loop = loop or get_running_loop()
        except RuntimeError:
            self.loop = None
        self._executor = None

    @property
    def executor(self):
        if not self._executor:
            self._executor = ProcessPoolExecutor()
        return self._executor

    @classmethod
    async def from_context(cls, ctx: commands.Context):
        targets = await Targets(ctx).targets()
        if targets:
            return cls(*targets, loop=ctx.bot.loop)
        else:
            raise NoTarget("Could not find any targets!")

    def add(self, source: BytesIO) -> None:
        self.sources.append(source)

    def thread(func):
        """ Runs a function in another thread, returns a Future """
        @wraps(func)
        def wrapper(*args, **kwargs) -> Future:
            return args[0].loop.run_in_executor(None, partial(func, *args, **kwargs))
        return wrapper

    def targets(targets=1):
        def inner(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                if len(args[0].sources) < targets:
                    raise NoTarget(f"Requires {targets} targets")
                return func(*args, **kwargs)
            return wrapper
        return inner

    def isshade(self, color1: tuple, color2: tuple, threshold=100):
        """ Checks if the first RGB tuple is a shade of the second RGB tuple """
        for i in range(len(color1)):
            if abs(color2[i]-color1[i]) > threshold:
                return False
        return True

    def islight(self, image: Image, threshold=100):
        black = white = 0
        for pixel in image.getdata():
            if pixel < threshold:
                black += 1
            else:
                white += 1
        return white > black


    def to_buffer(self, image: Image) -> BytesIO:
        """ Takes Image and returns BytesIO. Please ensure this function is called in another thread to avoid blocking """
        buffer = BytesIO()
        image.save(buffer, format='gif')
        buffer.seek(0)
        return buffer

    @targets(1)
    @thread
    def invert(self) -> BytesIO:
        image = Image.open(self.sources[0]).convert('RGB')
        inverted = ImageOps.invert(image)
        return self.to_buffer(inverted)
    
    @targets(2)
    @thread
    def blend(self):
        primary = Image.open(self.sources[0]).convert('RGB')
        secondary = Image.open(self.sources[1]).convert('RGB').resize(primary.size)
        blended = Image.blend(primary, secondary, alpha=0.5)
        return self.to_buffer(blended)

    @targets(1)
    @thread
    def crop(self, pixels: int):
        image = Image.open(self.sources[0])
        cropped = ImageOps.crop(image, border=pixels)
        return self.to_buffer(cropped)

    @targets(1)
    @thread
    def border(self, width: int, color: Color):
        image = Image.open(self.sources[0])
        return self.to_buffer(ImageOps.expand(image, border=width, fill=color.to_rgb()))

    @targets(2)
    @thread
    def lighter(self):
        image = Image.open(self.sources[0]).convert('RGBA')
        other = Image.open(self.sources[1]).convert('RGBA').resize(image.size)
        return self.to_buffer(ImageChops.lighter(image, other))

    @targets(2)
    @thread
    def darker(self):
        image = Image.open(self.sources[0]).convert('RGBA')
        other = Image.open(self.sources[1]).resize(image.size).convert('RGBA')
        return self.to_buffer(ImageChops.darker(image, other))

    @targets(2)
    @thread
    def subtract(self):
        image = Image.open(self.sources[0]).convert('RGBA')
        other = Image.open(self.sources[1]).resize(image.size).convert('RGBA')
        return self.to_buffer(ImageChops.subtract_modulo(image, other))

    @targets(1)
    @thread
    def contour(self):
        image = Image.open(self.sources[0]).convert("RGB")
        return self.to_buffer(image.filter(ImageFilter.CONTOUR))

    @targets(1)
    @thread
    def edges(self):
        image = Image.open(self.sources[0]).convert("RGB")
        return self.to_buffer(image.filter(ImageFilter.FIND_EDGES))

    @targets(1)
    @thread
    def emboss(self):
        image = Image.open(self.sources[0])
        return self.to_buffer(image.filter(ImageFilter.EMBOSS))

    @targets(1)
    @thread
    def replace(self, og: Color, to: Color):
        image = Image.open(self.sources[0])
        for x in range(image.size[0]):
            for y in range(image.size[1]):
                now = image.getpixel((x,y))
                if self.isshade(now, og.to_rgb()):
                    image.putpixel((x,y), to.to_rgb())
        return self.to_buffer(image)

    @targets(1)
    @thread
    def smooth(self):
        image = Image.open(self.sources[0])
        return self.to_buffer(image.filter(ImageFilter.SMOOTH_MORE))
    
    @targets(1)
    @thread
    def blur(self):
        image = Image.open(self.sources[0])
        return self.to_buffer(image.filter(ImageFilter.BLUR))

    @targets(1)
    @thread 
    def gaussianblur(self, radius: int):
        image = Image.open(self.sources[0])
        return self.to_buffer(image.filter(ImageFilter.GaussianBlur(radius)))

    @targets(1)
    @thread
    def adjust(self, **kwargs):
        image = Image.open(self.sources[0]).convert('RGBA')
        methods = {'brightness': ImageEnhance.Brightness, 'color': ImageEnhance.Color, 'contrast': ImageEnhance.Contrast, 'sharpness': ImageEnhance.Sharpness}
        for method, value in kwargs.items():
            if value != 1.0:
                image = methods[method](image).enhance(value)
        return self.to_buffer(image)

    @targets(1)
    @thread
    def removebg(self):
        image = Image.open(self.sources[0]).convert('RGBA')
        edges = ImageOps.grayscale(image)
        if not self.islight(edges, threshold=127.5):
            edges = ImageOps.invert(edges)
        _x, _y = edges.size
        for x in range(_x):
            for y in range(_y):
                pixel = edges.getpixel((x, y))
                if not self.isshade((pixel,), (0,), threshold=127.5):
                    image.putpixel((x, y), (255, 255, 255, 0))
        return self.to_buffer(image)

    @targets(1)
    @thread
    def pdf(self):
        image = Image.open(self.sources[0]).convert('RGB')
        buffer = BytesIO()
        image.save(buffer, format='pdf')
        buffer.seek(0)
        return buffer

    @thread
    def merge_pdfs(self, options: set):
        merger = PdfFileMerger()
        for source in self.sources:
            image = Image.open(source).convert('RGB')
            if 'rotate-all' in options:
                image = image.rotate(90, expand=True)
            buffer = BytesIO()
            image.save(buffer, format='pdf')
            buffer.seek(0)
            merger.append(PdfFileReader(buffer))
        buffer = BytesIO()
        merger.write(buffer)
        buffer.seek(0)
        return buffer

    @thread
    def make_qr(self, message):
        qr = pyqrcode.create(message)
        buffer = BytesIO()
        qr.png(buffer)
        buffer.seek(0)
        image = Image.open(buffer)
        new = image.resize((image.width*4, image.height*4))
        resized_buffer = BytesIO()
        new.save(resized_buffer, format='png')
        resized_buffer.seek(0)
        return resized_buffer

        
class InvalidOperation(Exception):
    """ Raised when an non-existent operation is used. """
             
class Palette:
    def __init__(self, ctx):
        self.ctx = ctx

class PaletteView(View):
    def __init__(self, ctx, target):
        super().__init__()
        self.ctx = ctx
        self.machine = Machine(target)

    @select(placeholder="Image Filters")
    async def image_filters(self, select, interaction):
        return

class ConfirmView(View):
    def __init__(self, ctx, session):
        super().__init__()
        self.ctx = ctx
        self.session = session
        self.continued = False

    @button(label='Yes', style=ButtonStyle.success)
    async def yes(self, button, interaction):
        await interaction.message.channel.send(file=await self.session.compile())
        self.stop()

    @button(label='No', style=ButtonStyle.danger)
    async def no(self, button, interaction):
        self.continued = True
        self.stop()

    async def interaction_check(self, interaction):
        if interaction.user == self.ctx.author:
            return True
        else:
            await interaction.response.send_message("You cannot interact with someone else's command!", ephemeral=True)

class Images(commands.Cog):
    """Professional grade image editing tools brought to you. Multi-threaded, blazing-fast and intuitive."""

    def __init__(self, bot):
        self.bot = bot
        self.sessions = {}

    async def auto(self, ctx, *args, **kwargs):
        """Calls Machine.`command name`, and handles errors. The args and kwargs passed here are passed directly to the operation method"""
        async with ctx.typing():
            try:
                machine = await Machine.from_context(ctx)
                res = await getattr(machine, ctx.command.name)(*args, **kwargs)
                file = File(res, filename=f"{ctx.command.name}.png")
                await ctx.send(file=file)
            except NoTarget as e:
                return await ctx.send(str(e), delete_after=10)
            except AttributeError:
                raise InvalidOperation(f"Invalid Image Operation! {ctx.author} used {ctx.command.qualified_name}.")

    async def cog_command_error(self, ctx, error):
        error = getattr(error, 'original', error)
        if isinstance(error, InvalidOperation):
            await ctx.send(f"I couldn't find the operation {ctx.command.qualified_name}, I have notified my developers!") 
        elif isinstance(error, UnidentifiedImageError):
            await ctx.send("Could not parse the given image!")
        elif isinstance(error, BadColourArgument):
            await ctx.send("Couldn't find that color! Try using a hexadecimal value instead.")
        elif isinstance(error, flags.ArgumentParsingError):
            await ctx.send("Couldn't parse those arguments... did you forget a `-`?")
        else:
            raise error

    @commands.command(aliases=('darken', 'darkmode', 'kindadarkmode'), description="Inverts the colors of an image. You can reply to a message with an image, tag a user, pass a custom emoji, or provide a message id or user id.")
    async def invert(self, ctx, target: MODELS):
        await self.auto(ctx)

    @commands.command(description="Blends two images.")
    async def blend(self, ctx, target: MODELS, other: MODELS):
        await self.auto(ctx)

    @commands.command(description="Removes the given amount of pixels from each side of the image.")
    async def crop(self, ctx, target: MODELS, pixels: int=50):
        await self.auto(ctx, pixels)

    @commands.command(description="Adds a border frame to the image. You can set the width in pixels, and the color.")
    async def border(self, ctx, target: MODELS, width: int, color: Color):
        await self.auto(ctx, width, color)

    @commands.command(description="Compares the pixels of two images and creates an image with all the lighter pixels.")
    async def lighter(self, ctx, target: MODELS, target2: MODELS):
        await self.auto(ctx)
    
    @commands.command(description="Subtracts the RGB values of each pixel of one image from another and creates an image with the resultant RGB values.")
    async def subtract(self, ctx, target: MODELS, target2: MODELS):
        await self.auto(ctx)

    @commands.command(description="Compares the pixels of two images and creates an image with all the darker pixels.")
    async def darker(self, ctx, target: MODELS, target2: MODELS):
        await self.auto(ctx)
        
    @commands.command(description="Creates an image with the contours of the given image.")
    async def contour(self, ctx, target: MODELS):
        await self.auto(ctx)

    @commands.command(description="Creates an image with only edges from the given image.")
    async def edges(self, ctx, target: MODELS):
        await self.auto(ctx)

    @commands.command(description="Embosses the given image.", aliases=['carbonite'])
    async def emboss(self, ctx, target: MODELS):
        await self.auto(ctx)

    @commands.command(description="Replaces pixels of a color with another color.")
    async def replace(self, ctx, target: MODELS, og: Color, to: Color):
        await self.auto(ctx, og, to)

    @commands.command(description="Smooths the image.")
    async def smooth(self, ctx, target: MODELS):
        await self.auto(ctx)

    @commands.command(description="Blurs the image.")
    async def blur(self, ctx, target: MODELS):
        await self.auto(ctx)

    @commands.command(description="Applies a gaussian blur on the given radius.")
    async def gaussianblur(self, ctx, target: MODELS, radius: int):
        await self.auto(ctx, radius)

    @flags.add_flag("-brightness", type=float, default=1.0)
    @flags.add_flag("-color", type=float, default=1.0)
    @flags.add_flag("-sharpness", type=float, default=1.0)
    @flags.add_flag("-contrast", type=float, default=1.0)
    @flags.command(description="Adjusts an image with the given parameters (brightness, contrast, color, sharpness). The values given should be floats (1.0, 1.5, etc).")
    async def adjust(self, ctx, target: MODELS, **flags):
        await self.auto(ctx, **flags)

    @commands.command(aliases=['removebackground'], description="Removes the background of an image. This is experimental!")
    async def removebg(self, ctx, target: MODELS):
        await self.auto(ctx)

    @commands.group(invoke_without_command=True)
    async def qr(self, ctx):
        await ctx.send("Use `hk qr make` to make a QR code and `hk qr read` to read one!", delete_after=10)

    @qr.command()
    async def make(self, ctx, *, message: str):
        machine = Machine(loop=ctx.bot.loop)
        await ctx.send(file=File(await machine.make_qr(message), filename='QR.png'))

    @commands.group(invoke_without_command=True)
    async def pdf(self, ctx):
        if ctx.author.id in self.sessions:
            await ctx.send("Your old session was deleted and a new session was created!")
        else:
            await ctx.send("A new session was created!")
        self.sessions[ctx.author.id] = Machine(loop=self.bot.loop)
    
    @pdf.command()
    async def stop(self, ctx, *options: set):
        if not ctx.author.id in self.sessions:
            return await ctx.send("You don't have a session open!")
        
        mach: Machine = self.sessions[ctx.author.id]
        file = File(await mach.merge_pdfs(options=options), filename='merged.pdf')
        await ctx.send("Compiled successfully!", file=file)
        del self.sessions[ctx.author.id]

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        if (mach := self.sessions.get(message.author.id)) and message.attachments:
            for att in message.attachments:
                mach.sources.append(BytesIO(await att.read()))
    

            
        











def setup(bot):
    bot.add_cog(Images(bot))