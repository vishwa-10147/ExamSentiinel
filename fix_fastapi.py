with open('backend/app/api/questions.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('import io, Depends, HTTPException, Query, status', 'import io\nfrom fastapi import Depends, HTTPException, Query, status')

with open('backend/app/api/questions.py', 'w', encoding='utf-8') as f:
    f.write(text)
