import sys

with open(r'backend\app\schemas\code_execution.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace(
    'language: Literal["python", "javascript"]',
    'language: str'
)

# Also add question_id for SQL schema fetching
text = text.replace(
    'session_id: uuid.UUID',
    'session_id: uuid.UUID\n    question_id: Optional[uuid.UUID] = None'
)

with open(r'backend\app\schemas\code_execution.py', 'w', encoding='utf-8') as f:
    f.write(text)
