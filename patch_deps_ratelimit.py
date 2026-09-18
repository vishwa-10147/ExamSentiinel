import sys

with open(r'backend\app\api\deps.py', 'r') as f:
    text = f.read()

rate_limit_code = '''
from app.core.redis_client import redis_client
import time
from fastapi import Request

def RateLimiter(calls: int, period: int):
    """
    Sliding window rate limiter using Redis.
    calls: max number of requests allowed.
    period: time window in seconds.
    """
    async def rate_limit_dependency(request: Request):
        client_ip = request.client.host if request.client else "127.0.0.1"
        # Fallback to forwarded headers if behind proxy
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0]
            
        key = f"rate_limit:{request.url.path}:{client_ip}"
        now = time.time()
        
        # Redis MULTI/EXEC block for sliding window
        async with redis_client.pipeline(transaction=True) as pipe:
            # Remove scores older than (now - period)
            pipe.zremrangebyscore(key, 0, now - period)
            # Add current request timestamp
            pipe.zadd(key, {str(now): now})
            # Count requests in window
            pipe.zcard(key)
            # Set expiry to prevent lingering keys
            pipe.expire(key, period)
            
            results = await pipe.execute()
            
        request_count = results[2]
        
        if request_count > calls:
            raise HTTPException(
                status_code=429,
                detail="Too Many Requests. Please try again later."
            )
            
    return rate_limit_dependency
'''

with open(r'backend\app\api\deps.py', 'w') as f:
    f.write(text + "\n" + rate_limit_code)
