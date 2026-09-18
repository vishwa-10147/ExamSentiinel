import sys

with open(r'backend\app\api\router.py', 'r') as f:
    text = f.read()

# Fix the broken newlines that powershell messed up
text = text.replace('\\n', '\n')

with open(r'backend\app\api\router.py', 'w') as f:
    f.write(text)
