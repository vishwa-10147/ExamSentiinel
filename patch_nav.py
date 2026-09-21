import sys

with open("frontend/components/Navbar.tsx", "r", encoding="utf-8") as f:
    text = f.read()

# Fix toggleSidebar hook
if 'useSidebar' not in text:
    text = text.replace('import { useAuth } from "@/contexts/AuthContext";', 'import { useSidebar } from "@/contexts/SidebarContext";\nimport { useAuth } from "@/contexts/AuthContext";')
if 'toggleSidebar' not in text:
    text = text.replace('const { user, isAuthenticated, logout } = useAuth();', 'const { user, isAuthenticated, logout } = useAuth();\n  const { isSidebarOpen, toggleSidebar } = useSidebar();')

# Fix missing Menu icon
if 'Menu' not in text:
    text = text.replace('AlertTriangle } from "lucide-react";', 'AlertTriangle, Menu } from "lucide-react";')

# Fix unclosed div
if '<div className="flex items-center gap-4">' in text and '</Link>\n        </div>\n        </div>' not in text:
    text = text.replace('</Link>\n\n        </div>\n', '</Link>\n        </div>\n        </div>\n')

with open("frontend/components/Navbar.tsx", "w", encoding="utf-8") as f:
    f.write(text)
