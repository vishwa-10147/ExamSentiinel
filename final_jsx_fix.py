def fix(path):
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()

    if 'Navbar' in path:
        if '<div className="flex items-center gap-4">' in text and '</Link>\n        </div>\n        </div>' not in text:
             text = text.replace('</Link>\n        </div>', '</Link>\n        </div>\n        </div>')

    if 'questions' in path:
        text = text.replace('<div className="flex-1 w-full">\n<main className="flex-1 flex flex-col overflow-y-auto">', '<main className="flex-1 flex flex-col overflow-y-auto">')

    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)

fix('frontend/components/Navbar.tsx')
fix('frontend/app/admin/questions/page.tsx')
