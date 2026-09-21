import os

files = [
    'frontend/app/auth/login/page.tsx',
    'frontend/app/auth/register/page.tsx'
]

for file in files:
    with open(file, 'r', encoding='utf-8') as f:
        text = f.read()

    # Container
    text = text.replace('bg-white', 'bg-white dark:bg-slate-800 dark:border-slate-700')
    # Text headers
    text = text.replace('text-slate-900', 'text-slate-900 dark:text-white')
    # Text descriptions
    text = text.replace('text-slate-500', 'text-slate-500 dark:text-slate-400')
    # Input labels
    text = text.replace('text-slate-700', 'text-slate-700 dark:text-slate-300')
    # Inputs
    text = text.replace('bg-slate-50', 'bg-slate-50 dark:bg-slate-900 dark:border-slate-700 dark:text-white dark:focus:border-blue-500 dark:focus:ring-blue-500/20')
    text = text.replace('border-slate-300', 'border-slate-300 dark:border-slate-700')

    with open(file, 'w', encoding='utf-8') as f:
        f.write(text)

print("Auth pages patched")
