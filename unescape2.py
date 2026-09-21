files = [
    'frontend/app/layout.tsx',
    'frontend/components/Navbar.tsx',
    'frontend/components/Sidebar.tsx',
    'frontend/app/admin/questions/page.tsx',
]
for fp in files:
    with open(fp, 'r', encoding='utf-8') as f:
        text = f.read()
    text = text.replace(r'\n', '\n')
    with open(fp, 'w', encoding='utf-8') as f:
        f.write(text)
print("Unescaped literal slashes")
