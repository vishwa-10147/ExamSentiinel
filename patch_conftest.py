import sys

with open(r'backend\tests\conftest.py', 'r') as f:
    text = f.read()

if 'StaticPool' not in text:
    text = text.replace('from sqlalchemy.ext.asyncio import AsyncSession', 'from sqlalchemy.pool import StaticPool\nfrom sqlalchemy.ext.asyncio import AsyncSession')
    
    old_engine = '''test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    future=True,
)'''
    new_engine = '''test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    future=True,
    poolclass=StaticPool,
    connect_args={"check_same_thread": False},
)'''
    text = text.replace(old_engine, new_engine)

with open(r'backend\tests\conftest.py', 'w') as f:
    f.write(text)
