import re

def clean_dashboard():
    with open('frontend/components/Dashboard.tsx', 'r', encoding='utf-8') as f:
        text = f.read()

    text = text.replace('<Sidebar />', '')
    text = text.replace('<div className="flex min-h-screen bg-slate-50">', '<div className="flex-1 w-full">')
    text = text.replace('<div className="flex-1 overflow-auto">', '<div className="w-full">')
    
    with open('frontend/components/Dashboard.tsx', 'w', encoding='utf-8') as f:
        f.write(text)

def clean_exam_page():
    with open('frontend/app/admin/exam/page.tsx', 'r', encoding='utf-8') as f:
        text = f.read()
    
    text = text.replace('<Sidebar />', '')
    text = text.replace('<div className="flex flex-1">', '<div className="flex-1 w-full">')
    text = text.replace('<div className="flex-1 p-6 sm:p-8 max-w-7xl">', '<div className="w-full">')
    
    with open('frontend/app/admin/exam/page.tsx', 'w', encoding='utf-8') as f:
        f.write(text)

clean_dashboard()
clean_exam_page()
