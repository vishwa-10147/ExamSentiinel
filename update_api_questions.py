import re

filepath = 'backend/app/api/questions.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

import_csv = '''
import csv
import io
from fastapi import UploadFile, File
'''

if 'UploadFile' not in content:
    content = content.replace('from fastapi import APIRouter', 'from fastapi import APIRouter, UploadFile, File, BackgroundTasks\nimport csv\nimport io')

bulk_endpoint = '''
@router.post("/bulk", response_model=dict)
async def bulk_upload_questions(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN]))
):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed.")
    
    contents = await file.read()
    try:
        text = contents.decode('utf-8')
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="CSV must be UTF-8 encoded.")
        
    reader = csv.DictReader(io.StringIO(text))
    questions_to_insert = []
    
    for row in reader:
        # Expected CSV columns: title, content, type, difficulty, points, options, correct_answer
        try:
            q = Question(
                id=uuid.uuid4(),
                title=row.get('title', '').strip(),
                content=row.get('content', '').strip(),
                type=QuestionType(row.get('type', 'multiple_choice')),
                difficulty=QuestionDifficulty(row.get('difficulty', 'medium')),
                points=int(row.get('points', 10)),
                options=row.get('options', '').split('|') if row.get('options') else [],
                correct_answer=row.get('correct_answer', '').strip(),
                rubric=row.get('rubric', None)
            )
            questions_to_insert.append(q)
        except Exception as e:
            continue # skip invalid rows
            
    if not questions_to_insert:
        raise HTTPException(status_code=400, detail="No valid questions found in CSV.")
        
    db.add_all(questions_to_insert)
    await db.commit()
    
    return {"status": "success", "inserted": len(questions_to_insert)}
'''

if '@router.post("/bulk"' not in content:
    content += '\n' + bulk_endpoint

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print('Updated questions.py')
