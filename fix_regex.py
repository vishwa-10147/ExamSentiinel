import re

files = [
    'frontend/app/admin/questions/page.tsx',
    'frontend/app/candidate/practice/page.tsx',
    'frontend/app/exam/[id]/lab/page.tsx'
]

for filepath in files:
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()
    
    # Fix fetch(..., {
    text = re.sub(r'fetch\(\$\{([^}]+)\}([^,]+),\s*\{', r'fetch(\\2, {', text)
    
    # Fix headers: { "Authorization": Bearer \ }
    text = re.sub(r'\"Authorization\":\s*Bearer\s*\\\s*\}', r'"Authorization": Bearer  }', text)
    
    # Fix Authorization in lab exam page which might be Bearer \ },
    text = re.sub(r'\"Authorization\":\s*Bearer\s*\\\s*\},', r'"Authorization": Bearer  },', text)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(text)
print('Fixed backticks with regex')
