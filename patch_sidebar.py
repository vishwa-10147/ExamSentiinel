import re

with open('frontend/components/Sidebar.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('bg-white', 'bg-white dark:bg-slate-900')
text = text.replace('border-slate-200', 'border-slate-200 dark:border-slate-700')
text = text.replace('text-slate-400', 'text-slate-400 dark:text-slate-500')
text = text.replace('text-slate-500', 'text-slate-500 dark:text-slate-400')
text = text.replace('text-slate-600', 'text-slate-600 dark:text-slate-300')
text = text.replace('text-slate-700', 'text-slate-700 dark:text-slate-200')
text = text.replace('bg-slate-50', 'bg-slate-50 dark:bg-slate-800')
text = text.replace('bg-blue-50 text-blue-700', 'bg-blue-50 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300')
text = text.replace('hover:bg-slate-50 text-slate-600', 'hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300')

with open('frontend/components/Sidebar.tsx', 'w', encoding='utf-8') as f:
    f.write(text)
