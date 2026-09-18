import sys
import re

with open(r'backend\app\api\code_execution.py', 'r', encoding='utf-8') as f:
    text = f.read()

execute_logic = '''
    database_setup = ""
    if payload.language == "sql" and payload.question_id:
        from app.models.question import Question
        q = (await db.execute(select(Question).where(Question.id == payload.question_id))).scalar_one_or_none()
        if q and q.database_schema:
            database_setup = q.database_schema
            if q.database_seed:
                database_setup += "\\n" + q.database_seed

    try:
        result = sandbox_service.execute(
            payload.language, 
            payload.source_code, 
            payload.stdin, 
            payload.time_limit_sec, 
            payload.memory_limit_mb,
            database_setup=database_setup
        )
    except
'''

text = re.sub(
    r'    try:\n        result = sandbox_service.execute.*?except',
    execute_logic.strip(),
    text,
    flags=re.DOTALL
)

with open(r'backend\app\api\code_execution.py', 'w', encoding='utf-8') as f:
    f.write(text)
