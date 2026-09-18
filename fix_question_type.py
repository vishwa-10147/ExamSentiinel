import sys

with open(r'frontend\services\examService.ts', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace(
    'export type QuestionType = "MCQ_SINGLE" | "MCQ_MULTI" | "SHORT_ANSWER" | "ESSAY" | "CODING";',
    'export type QuestionType = "MCQ_SINGLE" | "MCQ_MULTI" | "SHORT_ANSWER" | "ESSAY" | "CODING" | "SQL";'
)

with open(r'frontend\services\examService.ts', 'w', encoding='utf-8') as f:
    f.write(text)
