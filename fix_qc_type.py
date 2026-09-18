import sys

with open(r'frontend\components\exam\QuestionCard.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace(
    'const data = await apiClient.post("/api/code/execute", {',
    'const data = await apiClient.post<any>("/api/code/execute", {'
)

with open(r'frontend\components\exam\QuestionCard.tsx', 'w', encoding='utf-8') as f:
    f.write(text)
