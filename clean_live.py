import re

filepath = 'frontend/components/LiveProctoring.tsx'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

content = re.sub(r'import Sidebar from ["\']@/components/Sidebar["\'];\n?', '', content)
content = re.sub(r'\s*<Sidebar />\s*', '\n', content)

# LiveProctoring layout specific:
content = re.sub(r'<div className="flex min-h-screen bg-slate-50">\s*<main className="flex-1 (.*?)">', r'<div className="w-full \1">', content)
content = re.sub(r'<div className="flex min-h-screen bg-slate-50">', '<div className="w-full">', content)
content = re.sub(r'<main className="flex-1 (.*?)">', r'<div className="w-full \1">', content)
content = content.replace('</main>', '</div>')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Cleaned LiveProctoring.tsx")
