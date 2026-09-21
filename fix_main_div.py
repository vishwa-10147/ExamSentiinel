with open('frontend/app/admin/questions/page.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('<main className="flex-1 flex flex-col overflow-y-auto">', '<div className="flex-1 flex flex-col overflow-y-auto">')

with open('frontend/app/admin/questions/page.tsx', 'w', encoding='utf-8') as f:
    f.write(text)
