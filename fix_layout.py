import sys

with open(r'frontend\app\layout.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('className="bg-slate-50 dark:bg-slate-900 min-h-screen text-slate-900 dark:text-slate-50 antialiased font-sans transition-colors duration-200"', 
                    'className="bg-slate-50 dark:bg-slate-900 min-h-screen text-slate-900 dark:text-slate-50 antialiased font-sans transition-colors duration-200 overflow-x-hidden"')

with open(r'frontend\app\layout.tsx', 'w', encoding='utf-8') as f:
    f.write(text)
