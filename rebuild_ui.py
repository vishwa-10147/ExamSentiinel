import os

# 1. SidebarContext
os.makedirs("frontend/contexts", exist_ok=True)
with open("frontend/contexts/SidebarContext.tsx", "w", encoding="utf-8") as f:
    f.write('''"use client";

import React, { createContext, useContext, useState, ReactNode } from "react";

interface SidebarContextType {
  isSidebarOpen: boolean;
  toggleSidebar: () => void;
  setSidebarOpen: (isOpen: boolean) => void;
}

const SidebarContext = createContext<SidebarContextType | undefined>(undefined);

export function SidebarProvider({ children }: { children: ReactNode }) {
  const [isSidebarOpen, setSidebarOpen] = useState(true);

  const toggleSidebar = () => setSidebarOpen((prev) => !prev);

  return (
    <SidebarContext.Provider value={{ isSidebarOpen, toggleSidebar, setSidebarOpen }}>
      {children}
    </SidebarContext.Provider>
  );
}

export function useSidebar() {
  const context = useContext(SidebarContext);
  if (context === undefined) {
    throw new Error("useSidebar must be used within a SidebarProvider");
  }
  return context;
}
''')

# 2. Layout
with open("frontend/app/layout.tsx", "r", encoding="utf-8") as f:
    layout = f.read()
layout = layout.replace('import { AuthProvider } from "@/contexts/AuthContext";', 'import { AuthProvider } from "@/contexts/AuthContext";\\nimport { SidebarProvider } from "@/contexts/SidebarContext";')
layout = layout.replace('<AuthProvider>', '<AuthProvider>\\n          <SidebarProvider>')
layout = layout.replace('</AuthProvider>', '</SidebarProvider>\\n        </AuthProvider>')
with open("frontend/app/layout.tsx", "w", encoding="utf-8") as f:
    f.write(layout)

# 3. Navbar
with open("frontend/components/Navbar.tsx", "r", encoding="utf-8") as f:
    navbar = f.read()
navbar = navbar.replace('import { useAuth }', 'import { useSidebar } from "@/contexts/SidebarContext";\\nimport { useAuth }')
navbar = navbar.replace('AlertTriangle } from "lucide-react";', 'AlertTriangle, Menu } from "lucide-react";')
navbar = navbar.replace('const { user, isAuthenticated, logout } = useAuth();', 'const { user, isAuthenticated, logout } = useAuth();\\n  const { isSidebarOpen, toggleSidebar } = useSidebar();')
navbar = navbar.replace('<Link href="/" className="flex items-center gap-2">', '''<div className="flex items-center gap-4">
          {isAuthenticated && (
            <button
              onClick={toggleSidebar}
              className="p-2 rounded-md text-slate-500 hover:text-slate-900 hover:bg-slate-100 dark:text-slate-400 dark:hover:text-white dark:hover:bg-slate-800 transition-colors"
              aria-label="Toggle Sidebar"
            >
              <Menu className="h-6 w-6" />
            </button>
          )}
          <Link href="/" className="flex items-center gap-2">''')
navbar = navbar.replace('</Link>', '</Link>\\n        </div>')
with open("frontend/components/Navbar.tsx", "w", encoding="utf-8") as f:
    f.write(navbar)

# 4. Sidebar
with open("frontend/components/Sidebar.tsx", "r", encoding="utf-8") as f:
    sidebar = f.read()
sidebar = sidebar.replace('import { useAuth }', 'import { useSidebar } from "@/contexts/SidebarContext";\\nimport { useAuth }')
sidebar = sidebar.replace('const { user } = useAuth();', 'const { user } = useAuth();\\n  const { isSidebarOpen } = useSidebar();')
sidebar = sidebar.replace('<aside className="w-64 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 flex flex-col min-h-[calc(100vh-4rem)]">', '<aside className={g-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 flex flex-col min-h-[calc(100vh-4rem)] transition-all duration-300 ease-in-out }>')
sidebar = sidebar.replace('<nav className="flex-1 overflow-y-auto py-4">', '<nav className="flex-1 overflow-y-auto py-4 min-w-[16rem]">')
with open("frontend/components/Sidebar.tsx", "w", encoding="utf-8") as f:
    f.write(sidebar)

print("UI changes complete")
