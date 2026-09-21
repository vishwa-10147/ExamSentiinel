import re

with open('frontend/components/Navbar.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('bg-white/95', 'bg-white/95 dark:bg-slate-900/95')
text = text.replace('border-slate-200 bg-white', 'border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900')
text = text.replace('text-slate-900', 'text-slate-900 dark:text-white')
text = text.replace('border-slate-200', 'border-slate-200 dark:border-slate-700')
text = text.replace('bg-slate-50', 'bg-slate-50 dark:bg-slate-800')

with open('frontend/components/Navbar.tsx', 'w', encoding='utf-8') as f:
    f.write(text)
