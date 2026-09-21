with open('frontend/app/admin/questions/page.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('  return (\n    <div className="flex-1 w-full">\n    <main className="flex-1 flex flex-col overflow-y-auto">', '  return (\n    <>\n    <main className="flex-1 flex flex-col overflow-y-auto">')

text = text.replace('      )}\n    </div>\n    </div>\n  );\n}', '      )}\n    </>\n  );\n}')

with open('frontend/app/admin/questions/page.tsx', 'w', encoding='utf-8') as f:
    f.write(text)
