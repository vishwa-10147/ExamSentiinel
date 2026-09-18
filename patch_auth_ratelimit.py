import sys

with open(r'backend\app\api\auth.py', 'r') as f:
    text = f.read()

text = text.replace('@router.post("/login")', '@router.post("/login", dependencies=[Depends(RateLimiter(calls=5, period=60))])')

with open(r'backend\app\api\auth.py', 'w') as f:
    f.write(text)
