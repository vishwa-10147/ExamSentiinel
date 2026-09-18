import sys

with open(r'backend\app\api\auth.py', 'r') as f:
    text = f.read()

text = text.replace('from app.api.deps import get_current_user, get_db, log_audit_event', 'from app.api.deps import get_current_user, get_db, log_audit_event, RateLimiter')

with open(r'backend\app\api\auth.py', 'w') as f:
    f.write(text)
