import sys

with open(r'backend\app\api\auth.py', 'r') as f:
    text = f.read()

text = text.replace('from app.api.deps import get_db', 'from app.api.deps import get_db, RateLimiter')
text = text.replace('@router.post("/login", response_model=LoginResponse)', '@router.post("/login", response_model=LoginResponse, dependencies=[Depends(RateLimiter(calls=5, period=60))])')
text = text.replace('@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)', '@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RateLimiter(calls=3, period=3600))])')
text = text.replace('@router.post("/register", response_model=UserResponse, status_code=201)', '@router.post("/register", response_model=UserResponse, status_code=201, dependencies=[Depends(RateLimiter(calls=3, period=3600))])')
text = text.replace('@router.post("/forgot-password")', '@router.post("/forgot-password", dependencies=[Depends(RateLimiter(calls=3, period=600))])')

with open(r'backend\app\api\auth.py', 'w') as f:
    f.write(text)
