import redis.asyncio as redis
from app.core.config import settings

# Global Redis connection pool
redis_client = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)

async def get_redis():
    """Dependency injection for Redis client."""
    yield redis_client
