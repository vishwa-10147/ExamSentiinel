import sys

with open(r'backend\app\api\exams.py', 'r') as f:
    text = f.read()

new_class = '''from pydantic import BaseModel

class AIGenerateRequest(BaseModel):
    syllabus_text: str
    question_count: int = 5

router = APIRouter(prefix="/exams", tags=["Exams"])'''

text = text.replace('router = APIRouter(prefix="/exams", tags=["Exams"])', new_class)

with open(r'backend\app\api\exams.py', 'w') as f:
    f.write(text)
