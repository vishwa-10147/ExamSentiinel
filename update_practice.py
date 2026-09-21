import re

filepath = 'frontend/app/candidate/practice/page.tsx'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('"http://localhost:8000/api/sandbox/execute"', '${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/sandbox/execute')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated practice page API URL")
