import sys

with open(r'backend\tests\conftest.py', 'r') as f:
    text = f.read()

text = text.replace(
    'TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"',
    'TEST_DATABASE_URL = "sqlite+aiosqlite:///file:testdb?mode=memory&cache=shared&uri=true"'
)

with open(r'backend\tests\conftest.py', 'w') as f:
    f.write(text)
