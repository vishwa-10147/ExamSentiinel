with open('backend/app/api/proctoring.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('from typing import Optional', 'from typing import Optional\nfrom pydantic import BaseModel')

with open('backend/app/api/proctoring.py', 'w', encoding='utf-8') as f:
    f.write(text)
