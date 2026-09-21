import re

with open('frontend/components/Navbar.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('import ThemeToggle from "./ThemeToggle";\n"use client";', '"use client";\nimport ThemeToggle from "./ThemeToggle";')

with open('frontend/components/Navbar.tsx', 'w', encoding='utf-8') as f:
    f.write(text)
