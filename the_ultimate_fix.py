import sys

def fix_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    with open(filepath, 'w', encoding='utf-8') as f:
        for line in lines:
            if 'const res = await fetch(' in line and 'process.env.NEXT_PUBLIC_API_URL' in line:
                if 'questions' in filepath:
                    line = '      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/questions/bulk`, {\n'
                else:
                    line = '      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/sandbox/execute`, {\n'
            elif 'headers: { "Authorization": Bearer' in line or 'headers: { "Content-Type": "application/json", "Authorization": Bearer' in line:
                if 'Content-Type' in line:
                    line = '        headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },\n'
                else:
                    line = '        headers: { "Authorization": `Bearer ${token}` },\n'
            
            f.write(line)

fix_file('frontend/app/admin/questions/page.tsx')
fix_file('frontend/app/candidate/practice/page.tsx')
fix_file('frontend/app/exam/[id]/lab/page.tsx')
