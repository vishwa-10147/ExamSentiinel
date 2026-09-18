import sys
import re

with open(r'backend\app\services\sandbox_service.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Update signature
text = text.replace(
    'def execute(self, language: str, source_code: str, stdin: str, timeout_sec: float, memory_mb: int) -> SandboxResult:',
    'def execute(self, language: str, source_code: str, stdin: str, timeout_sec: float, memory_mb: int, database_setup: str = None) -> SandboxResult:'
)

# Add SQL language support
sql_support = '''        elif language == "c":
            compile_run = "mv source_file main.c && gcc -O2 main.c && ./a.out < stdin_file"
            image = os.getenv("SANDBOX_C_IMAGE", "gcc:13")
        elif language == "sql":
            # For SQL, we write the schema/seed to a setup file, create sqlite db, and run the query
            # We enforce sqlite3 output in markdown/box format for clean reading
            compile_run = "cat setup_sql > run.sql && echo '\n.mode box' >> run.sql && echo '.headers on' >> run.sql && cat source_file >> run.sql && sqlite3 db.sqlite < run.sql"
            image = os.getenv("SANDBOX_SQLITE_IMAGE", "nouchka/sqlite3:latest")
'''

text = re.sub(
    r'elif language == "c":.*?image = os.getenv\("SANDBOX_C_IMAGE", "gcc:13"\)',
    sql_support,
    text,
    flags=re.DOTALL
)

setup_b64 = '''
        setup_b64 = base64.b64encode((database_setup or "").encode('utf-8')).decode('utf-8')
        wrapper_script = f"""
echo "{source_b64}" | base64 -d > source_file
echo "{stdin_b64}" | base64 -d > stdin_file
echo "{setup_b64}" | base64 -d > setup_sql
"""
'''

text = re.sub(
    r'        wrapper_script = f"""\n.*?\n"""',
    setup_b64,
    text,
    flags=re.DOTALL
)

with open(r'backend\app\services\sandbox_service.py', 'w', encoding='utf-8') as f:
    f.write(text)
