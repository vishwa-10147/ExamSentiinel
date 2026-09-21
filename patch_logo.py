import re

with open('frontend/app/auth/login/page.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

text = re.sub(r'style=\{\{\s*width:\s*"auto",\s*height:\s*"auto"\s*\}\}', '', text)
text = text.replace('className="mx-auto drop-shadow-sm"', 'className="mx-auto h-20 w-auto object-contain drop-shadow-sm"')

with open('frontend/app/auth/login/page.tsx', 'w', encoding='utf-8') as f:
    f.write(text)

with open('frontend/components/Navbar.tsx', 'r', encoding='utf-8') as f:
    text2 = f.read()

text2 = re.sub(r'style=\{\{\s*width:\s*"auto",\s*height:\s*"auto"\s*\}\}', '', text2)
text2 = text2.replace('className="drop-shadow-sm"', 'className="h-10 w-auto object-contain drop-shadow-sm"')

with open('frontend/components/Navbar.tsx', 'w', encoding='utf-8') as f:
    f.write(text2)
