with open('frontend/app/admin/questions/page.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('  return (\n    <main className="flex-1 flex flex-col overflow-y-auto">', '  return (\n    <div className="flex-1 w-full">\n    <main className="flex-1 flex flex-col overflow-y-auto">')
text = text.replace('              Create Question\n            </button>\n          </div>\n\n          {error && (', '              Create Question\n            </button>\n          </div>\n          </div>\n\n          {error && (')
text = text.replace('      )}\n    </div>\n  );\n}', '      )}\n    </div>\n    </div>\n  );\n}')

# Fix fetch again just to be sure
text = text.replace('fetch(/api/questions/bulk, {', 'fetch(\\/api/questions/bulk, {')
text = text.replace('headers: { "Authorization": Bearer \\ },', 'headers: { "Authorization": Bearer \\ },')
text = text.replace('headers: { "Authorization": Bearer  },', 'headers: { "Authorization": Bearer \\ },')

with open('frontend/app/admin/questions/page.tsx', 'w', encoding='utf-8') as f:
    f.write(text)
