import sys

with open(r'frontend\app\admin\exam\[id]\grading\page.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace(
    'const res = await apiClient.post(`/api/reports/autograde/${responseId}`, {});',
    'const res = await apiClient.post<any>(`/api/reports/autograde/${responseId}`, {});'
)

with open(r'frontend\app\admin\exam\[id]\grading\page.tsx', 'w', encoding='utf-8') as f:
    f.write(text)
