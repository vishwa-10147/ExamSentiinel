import re

with open('backend/app/core/config.py', 'r', encoding='utf-8') as f:
    text = f.read()

validator_code = '''
    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v):
        if isinstance(v, str):
            if v.startswith("postgres://"):
                return v.replace("postgres://", "postgresql+asyncpg://", 1)
            if v.startswith("postgresql://") and not v.startswith("postgresql+asyncpg://"):
                return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v
'''

text = text.replace(
    'SYNC_DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5440/examsentinel"',
    'SYNC_DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5440/examsentinel"\n' + validator_code
)

with open('backend/app/core/config.py', 'w', encoding='utf-8') as f:
    f.write(text)
