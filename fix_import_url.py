import sys

with open(r'frontend\app\admin\exam\[id]\manage\page.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace(
    'await apiClient.upload(`/api/exams/${examId}/questions/bulk-import`, formData);',
    'await apiClient.upload(`/api/imports/questions/${examId}`, formData);'
)

with open(r'frontend\app\admin\exam\[id]\manage\page.tsx', 'w', encoding='utf-8') as f:
    f.write(text)
