with open('backend/app/api/proctoring.py', 'r', encoding='utf-8') as f:
    text = f.read()

if 'from pydantic import BaseModel' not in text:
    text = text.replace('from typing import List, Optional, Any', 'from typing import List, Optional, Any\nfrom pydantic import BaseModel')

with open('backend/app/api/proctoring.py', 'w', encoding='utf-8') as f:
    f.write(text)
