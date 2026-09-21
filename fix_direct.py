files = [
    'frontend/app/admin/questions/page.tsx',
    'frontend/app/candidate/practice/page.tsx',
    'frontend/app/exam/[id]/lab/page.tsx'
]

for filepath in files:
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    with open(filepath, 'w', encoding='utf-8') as f:
        for line in lines:
            if 'fetch(\\2, {' in line or 'fetch(' in line and 'process.env.NEXT_PUBLIC_API_URL' in line:
                if 'sandbox/execute' in filepath:
                    f.write('      const res = await fetch(\\/api/sandbox/execute, {\\n')
                elif 'questions/bulk' in filepath:
                    f.write('      const res = await fetch(\\/api/questions/bulk, {\\n')
                elif 'lab' in filepath:
                    f.write('      const res = await fetch(\\/api/sandbox/execute, {\\n')
                else:
                    f.write(line)
            elif 'headers: { "Authorization": Bearer  }' in line or 'headers: { "Authorization": Bearer \\ }' in line:
                f.write('        headers: { "Authorization": Bearer \\ },\\n')
            elif 'headers: { "Content-Type": "application/json", "Authorization": Bearer  }' in line or 'headers: { "Content-Type": "application/json", "Authorization": Bearer \\ },' in line:
                f.write('        headers: { "Content-Type": "application/json", "Authorization": Bearer \\ },\\n')
            else:
                f.write(line)

print("Rewrote lines directly")
