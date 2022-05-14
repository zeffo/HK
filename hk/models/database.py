from __future__ import annotations
from asyncpg import Connection, Record  # type: ignore
from asyncpg.pool import Pool  # type: ignore
import asyncio
from typing import Optional


class Client(Pool):
    def __init__(self, uri: str, loop: Optional[asyncio.AbstractEventLoop]=None):
        super().__init__(
            uri,
            connection_class=Connection,
            min_size=10,
            max_size=10,
            max_queries=50000,
            max_inactive_connection_lifetime=300.0,
            setup=None,
            init=None,
            loop=loop,
            record_class=Record # type: ignore
        )

    async def prepare(self) -> None:
        await self._async__init__()
        with open("hk/scripts/script.sql") as f:
            await self.execute(f.read())
