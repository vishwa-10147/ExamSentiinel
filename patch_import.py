import sys

with open(r'frontend\app\layout.tsx', 'r') as f:
    text = f.read()

text = 'import { ThemeProvider } from "@/components/ThemeProvider";\n' + text

with open(r'frontend\app\layout.tsx', 'w') as f:
    f.write(text)
