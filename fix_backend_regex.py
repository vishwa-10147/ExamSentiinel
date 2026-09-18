import re

with open(r'backend\app\api\exams.py', 'r') as f:
    text = f.read()

text = re.sub(r'request:\s*Request,\n+', '', text)
text = text.replace('print("HEADERS:", request.headers)\n    ', '')

with open(r'backend\app\api\exams.py', 'w') as f:
    f.write(text)
