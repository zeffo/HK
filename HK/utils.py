import sys, psutil, discord
from jishaku.modules import package_version
from jishaku.features.root_command import natural_size
from typing import Generator
from asyncio import get_running_loop
from re import match


def chunks(it: list, size: int) -> Generator:
    return (
        it[size * i : size * (i + 1)]
        for i, _ in enumerate(range(0, len(it) * size, size))
    )

def tmatch(regex, string):
    return get_running_loop().run_in_executor(None, match, regex, string)


def sysinfo(bot):
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
        guild_subscriptions = f"guild subscriptions are {'enabled' if bot._connection.guild_subscriptions else 'disabled'}"

        summary.append(f"{message_cache} and {guild_subscriptions}.")

    summary.append(f"Average websocket latency: {round(bot.latency * 1000, 2)}ms")
    summary.append(f"Cogs ({len(bot.cogs)}): {', '.join(bot.cogs)}")

    return "\n".join(summary)
