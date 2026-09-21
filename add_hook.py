with open('frontend/components/Navbar.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('  const { user, isAuthenticated, logout } = useAuth();\n  const [health, setHealth] = useState<HealthCheckResponse | null>(null);', '  const { user, isAuthenticated, logout } = useAuth();\n  const { isSidebarOpen, toggleSidebar } = useSidebar();\n  const [health, setHealth] = useState<HealthCheckResponse | null>(null);')

# Let's double check if my previous script added it somewhere else
if 'const { isSidebarOpen, toggleSidebar } = useSidebar();' not in text:
    text = text.replace('  const { user, isAuthenticated, logout } = useAuth();', '  const { user, isAuthenticated, logout } = useAuth();\n  const { isSidebarOpen, toggleSidebar } = useSidebar();')

with open('frontend/components/Navbar.tsx', 'w', encoding='utf-8') as f:
    f.write(text)
