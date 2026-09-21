import re

def fix(path):
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()
    
    text = re.sub(r'fetch\(\$\{process\.env\.NEXT_PUBLIC_API_URL \|\| "http://localhost:8000"\}/api/questions/bulk, \{', r'fetch(\/api/questions/bulk, {', text)
    text = re.sub(r'fetch\(\$\{process\.env\.NEXT_PUBLIC_API_URL \|\| "http://localhost:8000"\}/api/sandbox/execute, \{', r'fetch(\/api/sandbox/execute, {', text)
    text = re.sub(r'\"Authorization\":\s*Bearer\s*\\\s*\},?', r'"Authorization": Bearer \ },', text)
    text = re.sub(r'\"Authorization\":\s*Bearer\s*\},?', r'"Authorization": Bearer \ },', text)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)

fix('frontend/app/admin/questions/page.tsx')
fix('frontend/app/candidate/practice/page.tsx')
fix('frontend/app/exam/[id]/lab/page.tsx')

# Navbar
with open('frontend/components/Navbar.tsx', 'r', encoding='utf-8') as f:
    text = f.read()
if '<div className="flex items-center gap-4">' in text and '</Link>\n        </div>' not in text:
    text = text.replace('</Link>', '</Link>\n        </div>')
with open('frontend/components/Navbar.tsx', 'w', encoding='utf-8') as f:
    f.write(text)

print("regex fix")
