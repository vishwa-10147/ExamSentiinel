import sys

with open(r'frontend\components\exam\QuestionCard.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('className="flex-1 min-h-[300px]"', 'className="w-full h-[350px] md:h-[500px] border-b border-slate-700"')

with open(r'frontend\components\exam\QuestionCard.tsx', 'w', encoding='utf-8') as f:
    f.write(text)
