import sys
import re

with open(r'backend\tests\conftest.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Replace TEST_DATABASE_URL and engine creation
new_engine_setup = """import tempfile
import os

# Create a temporary file for the database
db_fd, db_path = tempfile.mkstemp(suffix=".sqlite")
os.close(db_fd)

TEST_DATABASE_URL = f"sqlite+aiosqlite:///{db_path}"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    future=True,
    # No StaticPool, use default pool so concurrent async tasks get their own connection
    connect_args={"check_same_thread": False},
)
"""

# Regex replace the old setup
text = re.sub(
    r'TEST_DATABASE_URL = .*?connect_args=\{"check_same_thread": False\},\n\)',
    new_engine_setup,
    text,
    flags=re.DOTALL
)

with open(r'backend\tests\conftest.py', 'w', encoding='utf-8') as f:
    f.write(text)
