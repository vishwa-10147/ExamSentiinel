import sys

with open(r'backend\app\models\question.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Add SQL to QuestionType
text = text.replace(
    'CODING = "CODING"',
    'CODING = "CODING"\n    SQL = "SQL"'
)

# Add database_schema and database_seed to Question
insert_fields = '''    rubric: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)

    # SQL Execution Engine specific fields
    database_schema: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    database_seed: Mapped[Optional[str]] = mapped_column(Text, nullable=True)'''

text = text.replace('    rubric: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)', insert_fields)

with open(r'backend\app\models\question.py', 'w', encoding='utf-8') as f:
    f.write(text)
