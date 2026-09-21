import re

files = [
    'frontend/app/admin/questions/page.tsx',
    'frontend/app/candidate/practice/page.tsx',
    'frontend/app/exam/[id]/lab/page.tsx'
]

for filepath in files:
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()
    
    text = text.replace('fetch(/api/questions/bulk, {', 'fetch(\\/api/questions/bulk, {')
    text = text.replace('fetch(/api/sandbox/execute, {', 'fetch(\\/api/sandbox/execute, {')

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(text)
print('Fixed backticks')
