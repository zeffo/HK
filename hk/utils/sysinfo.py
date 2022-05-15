import sys

import discord
import psutil
from discord.ext import commands
from jishaku.features.root_command import natural_size  # type: ignore
from jishaku.modules import package_version  # type: ignore


def sysinfo(bot: commands.Bot) -> str:
    """Taken and modified from jishaku.features.root_command"""

    summary = [
        f"Logged in as {bot.user}",
        f"discord.py {package_version('discord.py')}, "
        f"Python {sys.version} on {sys.platform}".replace("\n", ""),
        "",
    ]
    if psutil:
        try:
            proc = psutil.Process()
            with proc.oneshot():
                try:
                    mem = proc.memory_full_info()
                    summary.append(
                        f"Using {natural_size(mem.rss)} physical memory and "
                        f"{natural_size(mem.vms)} virtual memory, "
                        f"{natural_size(mem.uss)} of which unique to this process."
                    )
                except psutil.AccessDenied:
                    pass
                try:
                    name = proc.name()
                    pid = proc.pid
                    thread_count = proc.num_threads()

                    summary.append(
                        f"Running on PID {pid} ({name}) with {thread_count} thread(s)."
                    )
                except psutil.AccessDenied:
                    pass

                summary.append("")
        except psutil.AccessDenied:
            summary.append(
                "psutil is installed, but this process does not have high enough access rights "
                "to query process information."
            )
            summary.append("")

    cache_summary = f"{len(bot.guilds)} guild(s) and {len(bot.users)} user(s)"
    summary.append(f"This bot is not sharded and can see {cache_summary}.")

    if bot._connection.max_messages:
        message_cache = f"Message cache capped at {bot._connection.max_messages}"
    else:
        message_cache = "Message cache is disabled"

    if discord.version_info >= (1, 5, 0):
        presence_intent = (
            f"presence intent is {'enabled' if bot.intents.presences else 'disabled'}"
        )
        members_intent = (
            f"members intent is {'enabled' if bot.intents.members else 'disabled'}"
        )

        summary.append(f"{message_cache}, {presence_intent} and {members_intent}.")
    else:
        summary.append(message_cache)

    summary.append(f"Average websocket latency: {round(bot.latency * 1000, 2)}ms")
    summary.append(f"Cogs ({len(bot.cogs)}): {', '.join(bot.cogs)}")

    return "\n".join(summary)
