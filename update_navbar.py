with open('frontend/components/Navbar.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# Imports
if 'useSidebar' not in content:
    content = content.replace('import { useAuth }', 'import { useSidebar } from "@/contexts/SidebarContext";\nimport { useAuth }')

if 'Menu' not in content:
    content = content.replace('import { LogOut, Settings, User } from "lucide-react";', 'import { LogOut, Settings, User, Menu } from "lucide-react";')

# Inject hook
if 'const { isSidebarOpen' not in content:
    content = content.replace('const { isAuthenticated, user, logout } = useAuth();', 'const { isAuthenticated, user, logout } = useAuth();\n  const { isSidebarOpen, toggleSidebar } = useSidebar();')

# Inject hamburger button
hamburger = '''
        <div className="flex items-center gap-4">
          {isAuthenticated && (
            <button
              onClick={toggleSidebar}
              className="p-2 rounded-md text-slate-500 hover:text-slate-900 hover:bg-slate-100 dark:text-slate-400 dark:hover:text-white dark:hover:bg-slate-800 transition-colors"
              aria-label="Toggle Sidebar"
            >
              <Menu className="h-6 w-6" />
            </button>
          )}
          <Link href="/" className="flex items-center gap-2">
'''
content = content.replace('<Link href="/" className="flex items-center gap-2">', hamburger)
# Note: we need to make sure we don't duplicate if we run this twice. We just run once.

with open('frontend/components/Navbar.tsx', 'w', encoding='utf-8') as f:
    f.write(content)
print('Updated Navbar.tsx')
