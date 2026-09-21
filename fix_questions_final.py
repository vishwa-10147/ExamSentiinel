import sys
with open('frontend/app/admin/questions/page.tsx', 'r', encoding='utf-8') as f:
    lines = f.readlines()

with open('frontend/app/admin/questions/page.tsx', 'w', encoding='utf-8') as f:
    for line in lines:
        if 'const res = await fetch(' in line and 'api/questions/bulk' in line:
            line = '      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/questions/bulk`, {\n'
        elif 'headers: { "Authorization": Bearer' in line:
            line = '        headers: { "Authorization": `Bearer ${token}` },\n'
        f.write(line)
