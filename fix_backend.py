import sys

with open(r'backend\app\api\exams.py', 'r') as f:
    text = f.read()

old_sig = '''async def bulk_import_questions(
    request: Request,
    exam_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.PROCTOR])),
):
    print("HEADERS:", request.headers)
    exam_res = await db.execute'''

new_sig = '''async def bulk_import_questions(
    exam_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.PROCTOR])),
):
    exam_res = await db.execute'''

if old_sig in text:
    text = text.replace(old_sig, new_sig)
else:
    print("COULD NOT FIND BACKEND SIG")
    
with open(r'backend\app\api\exams.py', 'w') as f:
    f.write(text)
