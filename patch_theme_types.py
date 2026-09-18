import sys

with open(r'frontend\components\ThemeProvider.tsx', 'r') as f:
    text = f.read()

text = text.replace('import { ThemeProviderProps } from "next-themes/dist/types";', '')

with open(r'frontend\components\ThemeProvider.tsx', 'w') as f:
    f.write(text)
