import re

def rewrite(filepath, replacements):
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()
    for s, r in replacements:
        text = text.replace(s, r)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(text)

# 1. layout.tsx
rewrite('frontend/app/layout.tsx', [
    ('import { AuthProvider } from "@/contexts/AuthContext";\\nimport { SidebarProvider } from "@/contexts/SidebarContext";', 
     'import { AuthProvider } from "@/contexts/AuthContext";\nimport { SidebarProvider } from "@/contexts/SidebarContext";'),
    ('<AuthProvider>\\n          <SidebarProvider>', '<AuthProvider>\n          <SidebarProvider>'),
    ('</SidebarProvider>\\n        </AuthProvider>', '</SidebarProvider>\n        </AuthProvider>')
])

# 2. Sidebar.tsx
rewrite('frontend/components/Sidebar.tsx', [
    ('import { useSidebar } from "@/contexts/SidebarContext";\\nimport { useAuth } from "@/contexts/AuthContext";',
     'import { useSidebar } from "@/contexts/SidebarContext";\nimport { useAuth } from "@/contexts/AuthContext";'),
    ('const { user } = useAuth();\\n  const { isSidebarOpen } = useSidebar();',
     'const { user } = useAuth();\n  const { isSidebarOpen } = useSidebar();')
])

# 3. questions/page.tsx
rewrite('frontend/app/admin/questions/page.tsx', [
    ('import { Plus, Library, Trash2, Edit, AlertCircle, Type, BarChart, Upload } from "lucide-react";\\nimport { useRef } from "react";\\nimport toast from "react-hot-toast";',
     'import { Plus, Library, Trash2, Edit, AlertCircle, Type, BarChart, Upload } from "lucide-react";\nimport { useRef } from "react";\nimport toast from "react-hot-toast";')
])

# 4. practice/page.tsx
rewrite('frontend/app/candidate/practice/page.tsx', [
    ('fetch(\/api/sandbox/execute', 'fetch(${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/sandbox/execute'),
])

# 5. Navbar.tsx
rewrite('frontend/components/Navbar.tsx', [
    ('import { useSidebar } from "@/contexts/SidebarContext";\\nimport { useAuth }', 'import { useSidebar } from "@/contexts/SidebarContext";\nimport { useAuth }'),
    ('const { user, isAuthenticated, logout } = useAuth();\\n  const { isSidebarOpen, toggleSidebar } = useSidebar();', 'const { user, isAuthenticated, logout } = useAuth();\n  const { isSidebarOpen, toggleSidebar } = useSidebar();'),
    ('</Link>\\n        </div>', '</Link>\n        </div>')
])

print("Fixed newlines")
