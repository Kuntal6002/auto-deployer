import asyncpg
from arq.connections import RedisSettings
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    redis_url: str
    github_webhook_secret: str

    @property
    def arq_redis_settings(self) -> RedisSettings:
        # parse redis://redis:6379 → host=redis, port=6379
        url = self.redis_url.replace("redis://", "")
        host, port = url.split(":")
        return RedisSettings(host=host, port=int(port))

    class Config:
        env_file = ".env"


settings = Settings()


class Database:
    def __init__(self):
        self.pool: asyncpg.Pool | None = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(
            settings.database_url,
            min_size=2,
            max_size=10,
        )

    async def disconnect(self):
        if self.pool:
            await self.pool.close()

    async def fetch(self, query: str, *args):
        assert self.pool is not None
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args):
        assert self.pool is not None
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def execute(self, query: str, *args):
        assert self.pool is not None
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)


db = Database()
