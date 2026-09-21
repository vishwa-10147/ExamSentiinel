import os
import re

files_to_fix = [
    'frontend/app/admin/ai-test/page.tsx',
    'frontend/app/admin/analytics/page.tsx',
    'frontend/app/admin/audit/page.tsx',
    'frontend/app/admin/exam/builder/page.tsx',
    'frontend/app/admin/exam/[id]/manage/page.tsx',
    'frontend/app/admin/questions/page.tsx',
    'frontend/app/admin/settings/page.tsx',
    'frontend/app/admin/users/page.tsx'
]

for filepath in files_to_fix:
    if not os.path.exists(filepath):
        continue
        
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Remove the Sidebar import
    content = re.sub(r'import Sidebar from ["\']@/components/Sidebar["\'];\n?', '', content)
    
    # Remove the <Sidebar /> component
    content = re.sub(r'\s*<Sidebar />\s*', '\n', content)
    
    # Replace outer flex layout wrappers that were meant for the sidebar
    # Example: <div className="flex flex-1 h-screen overflow-hidden bg-slate-50">
    content = re.sub(r'<div className="flex flex-1 h-screen (?:overflow-hidden )?bg-slate-50">', '<div className="flex-1 w-full">', content)
    
    # Example: <div className="flex flex-1 h-screen">
    content = re.sub(r'<div className="flex flex-1 h-screen">', '<div className="flex-1 w-full">', content)
    
    # Example: <div className="flex flex-1">
    content = re.sub(r'<div className="flex flex-1">', '<div className="flex-1 w-full">', content)
    
    # Example: <div className="flex-1 overflow-y-auto bg-slate-50">
    content = re.sub(r'<div className="flex-1 overflow-y-auto bg-slate-50">', '<div className="w-full">', content)
    
    # Example: <div className="flex-1 overflow-y-auto">
    content = re.sub(r'<div className="flex-1 overflow-y-auto">', '<div className="w-full">', content)
    
    # Example: <div className="flex min-h-screen bg-slate-50">
    content = re.sub(r'<div className="flex min-h-screen bg-slate-50">', '<div className="flex-1 w-full">', content)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
        
print("Cleanup complete.")
