with open('frontend/components/Navbar.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

if 'useSidebar' not in text:
    text = text.replace('import { useAuth }', 'import { useSidebar } from "@/contexts/SidebarContext";\nimport { useAuth }')
if 'toggleSidebar' not in text:
    text = text.replace('const { user, isAuthenticated, logout } = useAuth();', 'const { user, isAuthenticated, logout } = useAuth();\n  const { isSidebarOpen, toggleSidebar } = useSidebar();')
if 'Menu }' not in text:
    text = text.replace('AlertTriangle }', 'AlertTriangle, Menu }')

with open('frontend/components/Navbar.tsx', 'w', encoding='utf-8') as f:
    f.write(text)
