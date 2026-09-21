import re

with open('frontend/components/Navbar.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

if 'Menu } from "lucide-react"' not in text:
    text = text.replace('AlertTriangle } from "lucide-react";', 'AlertTriangle, Menu } from "lucide-react";')

if 'const { isSidebarOpen, toggleSidebar }' not in text:
    text = text.replace('const { user, isAuthenticated, logout } = useAuth();', 'const { user, isAuthenticated, logout } = useAuth();\n  const { isSidebarOpen, toggleSidebar } = useSidebar();')

with open('frontend/components/Navbar.tsx', 'w', encoding='utf-8') as f:
    f.write(text)
print('Fixed Navbar hooks and imports')
