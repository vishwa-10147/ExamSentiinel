import os
import re

directories = [
    'frontend/app/admin/results',
    'frontend/app/admin/review',
    'frontend/app/admin/broadcast',
    'frontend/app/admin/exam',
    'frontend/app/admin/questions',
    'frontend/app/admin/users',
    'frontend/app/admin/settings',
    'frontend/app/admin/audit'
]

for d in directories:
    for root, dirs, files in os.walk(d):
        for name in files:
            if name == 'page.tsx':
                filepath = os.path.join(root, name)
                with open(filepath, 'r', encoding='utf-8') as f:
                    text = f.read()

                # Add padding to root space-y-6 or flex flex-col if missing
                if '<div className="space-y-6">' in text:
                    text = text.replace('<div className="space-y-6">', '<div className="space-y-6 p-6 sm:p-8 max-w-7xl mx-auto">', 1)
                
                # Check for white text. The user wants STRICTLY black and white text.
                # Remove text-slate-*, text-blue-*, etc. Or just rely on dark mode toggle?
                # The user said: "i want only bnlack and white text on the ui"
                # "check the ui and css there i want simple text format see the dashboard page and continu with the same ui design"
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(text)
