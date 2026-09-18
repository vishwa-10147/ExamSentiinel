import sys, re

with open(r'backend\app\api\deps.py', 'r') as f:
    text = f.read()

# I will replace the whole RateLimiter function since I know exactly what it should look like.
# Let's find def RateLimiter(calls: int, period: int): and replace until return rate_limit_dependency

pattern = re.compile(r'def RateLimiter\(calls: int, period: int\):.*?return rate_limit_dependency', re.DOTALL)

new_func = '''def RateLimiter(calls: int, period: int):
    """
    Returns a FastAPI dependency that implements a sliding window rate limit using Redis.
    Uses MULTI/EXEC pipeline to ensure atomicity.
    """
    async def rate_limit_dependency(request: Request):
        client_ip = request.client.host if request.client else "127.0.0.1"
        # Fallback to forwarded headers if behind proxy
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0]
            
        key = f"rate_limit:{request.url.path}:{client_ip}"
        now = time.time()
        
        try:
            # Redis MULTI/EXEC block for sliding window
            async with redis_client.pipeline(transaction=True) as pipe:
                # Remove scores older than (now - period)
                pipe.zremrangebyscore(key, 0, now - period)
                # Add current request timestamp
                pipe.zadd(key, {str(now): now})
                # Count requests in window
                pipe.zcard(key)
                # Set TTL to prevent stale keys
                pipe.expire(key, period)
                
                results = await pipe.execute()
                
            request_count = results[2]
            
            if request_count > calls:
                logger.warning("rate_limit_exceeded", ip=client_ip, path=request.url.path)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too Many Requests"
                )
        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            logger.debug(f"Redis rate limiter failed, bypassing: {e}")
            
    return rate_limit_dependency'''

text = pattern.sub(new_func, text)

with open(r'backend\app\api\deps.py', 'w') as f:
    f.write(text)
