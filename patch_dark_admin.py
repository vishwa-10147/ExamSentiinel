import os

directories = [
    'frontend/app/admin/exam',
    'frontend/app/admin/results',
    'frontend/app/admin/review'
]

for directory in directories:
    for root, dirs, files in os.walk(directory):
        for name in files:
            if name.endswith('.tsx') or name.endswith('.ts'):
                file_path = os.path.join(root, name)
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()

                # Containers
                text = text.replace('bg-white', 'bg-white dark:bg-slate-800 dark:border-slate-700')
                text = text.replace('bg-slate-50', 'bg-slate-50 dark:bg-slate-900')
                text = text.replace('bg-slate-100', 'bg-slate-100 dark:bg-slate-700')
                # Text
                text = text.replace('text-slate-900', 'text-slate-900 dark:text-white')
                text = text.replace('text-slate-800', 'text-slate-800 dark:text-slate-100')
                text = text.replace('text-slate-700', 'text-slate-700 dark:text-slate-200')
                text = text.replace('text-slate-600', 'text-slate-600 dark:text-slate-300')
                text = text.replace('text-slate-500', 'text-slate-500 dark:text-slate-400')
                text = text.replace('text-slate-400', 'text-slate-400 dark:text-slate-500')
                # Borders
                text = text.replace('border-slate-200', 'border-slate-200 dark:border-slate-700')
                text = text.replace('border-slate-300', 'border-slate-300 dark:border-slate-600')
                text = text.replace('divide-slate-200', 'divide-slate-200 dark:divide-slate-700')

                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(text)

print("Admin pages patched for dark mode")
