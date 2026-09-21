import os

def fix_file(filepath, replacements):
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()
    for s, r in replacements:
        text = text.replace(s, r)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(text)

fix_file('frontend/app/admin/questions/page.tsx', [
    ('fetch(/api/questions/bulk, {', 'fetch(\\/api/questions/bulk, {'),
    ('headers: { "Authorization": Bearer  },', 'headers: { "Authorization": Bearer \\ },')
])

fix_file('frontend/app/candidate/practice/page.tsx', [
    ('fetch(/api/sandbox/execute, {', 'fetch(\\/api/sandbox/execute, {')
])

fix_file('frontend/app/exam/[id]/lab/page.tsx', [
    ('fetch(/api/sandbox/execute, {', 'fetch(\\/api/sandbox/execute, {'),
    ('headers: { "Content-Type": "application/json", "Authorization": Bearer  },', 'headers: { "Content-Type": "application/json", "Authorization": Bearer \\ },')
])

fix_file('frontend/components/Navbar.tsx', [
    ('</Link>\n          </div>', '</Link>\n        </div>\n          </div>')
])

print("Fixed syntax errors directly")
