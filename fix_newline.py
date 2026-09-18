import sys

with open(r'backend\app\api\deps.py', 'r') as f:
    text = f.read()

text = text.replace('from app.core.config import settings\\nfrom app.core.logging import logger', 'from app.core.config import settings\nfrom app.core.logging import logger')

with open(r'backend\app\api\deps.py', 'w') as f:
    f.write(text)
