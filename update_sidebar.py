import re

with open('frontend/components/Sidebar.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

if 'useSidebar' not in content:
    content = content.replace('import { useAuth }', 'import { useSidebar } from "@/contexts/SidebarContext";\nimport { useAuth }')

if 'const { isSidebarOpen' not in content:
    content = content.replace('const { user } = useAuth();', 'const { user } = useAuth();\n  const { isSidebarOpen } = useSidebar();')

# Modify the root div classes
old_class = '<aside className="w-64 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 flex flex-col min-h-[calc(100vh-4rem)]">'
new_class = '<aside className={g-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 flex flex-col min-h-[calc(100vh-4rem)] transition-all duration-300 ease-in-out }>'

content = content.replace(old_class, new_class)

# Ensure no text wrapping when closed by applying min-w to inner nav
nav_old = '<nav className="flex-1 overflow-y-auto py-4">'
nav_new = '<nav className="flex-1 overflow-y-auto py-4 min-w-[16rem]">'
content = content.replace(nav_old, nav_new)

with open('frontend/components/Sidebar.tsx', 'w', encoding='utf-8') as f:
    f.write(content)
print('Updated Sidebar.tsx')
