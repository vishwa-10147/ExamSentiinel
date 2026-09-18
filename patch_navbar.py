import sys

with open(r'frontend\components\Navbar.tsx', 'r') as f:
    text = f.read()

text = 'import ThemeToggle from "./ThemeToggle";\n' + text

old_nav = '''          <div className="flex items-center space-x-4">
            {isAuthenticated && user ? ('''

new_nav = '''          <div className="flex items-center space-x-4">
            <ThemeToggle />
            {isAuthenticated && user ? ('''

text = text.replace(old_nav, new_nav)

with open(r'frontend\components\Navbar.tsx', 'w') as f:
    f.write(text)
