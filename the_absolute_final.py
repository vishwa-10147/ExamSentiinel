with open('frontend/app/admin/questions/page.tsx', 'r', encoding='utf-8') as f:
    text = f.read()
text = text.replace('fetch(/api/questions/bulk, {', 'fetch(\\/api/questions/bulk, {')
text = text.replace('headers: { "Authorization": Bearer \ },', 'headers: { "Authorization": Bearer \\ },')
text = text.replace('headers: { "Authorization": Bearer \\ },', 'headers: { "Authorization": Bearer \\ },')
with open('frontend/app/admin/questions/page.tsx', 'w', encoding='utf-8') as f:
    f.write(text)

with open('frontend/app/candidate/practice/page.tsx', 'r', encoding='utf-8') as f:
    text = f.read()
text = text.replace('fetch(/api/sandbox/execute, {', 'fetch(\\/api/sandbox/execute, {')
with open('frontend/app/candidate/practice/page.tsx', 'w', encoding='utf-8') as f:
    f.write(text)

with open('frontend/app/exam/[id]/lab/page.tsx', 'r', encoding='utf-8') as f:
    text = f.read()
text = text.replace('fetch(/api/sandbox/execute, {', 'fetch(\\/api/sandbox/execute, {')
text = text.replace('headers: { "Content-Type": "application/json", "Authorization": Bearer \ },', 'headers: { "Content-Type": "application/json", "Authorization": Bearer \\ },')
text = text.replace('headers: { "Content-Type": "application/json", "Authorization": Bearer \\ },', 'headers: { "Content-Type": "application/json", "Authorization": Bearer \\ },')
with open('frontend/app/exam/[id]/lab/page.tsx', 'w', encoding='utf-8') as f:
    f.write(text)

with open('frontend/components/Navbar.tsx', 'r', encoding='utf-8') as f:
    text = f.read()
text = text.replace('</Link>\\n        </div>\\n          </div>', '</Link>\\n        </div>') # clean up
if '<div className="flex items-center gap-4">' in text and '</Link>\\n        </div>' not in text:
    text = text.replace('</Link>', '</Link>\\n        </div>')
with open('frontend/components/Navbar.tsx', 'w', encoding='utf-8') as f:
    f.write(text)
