import sys

with open(r'backend\app\models\institution.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace(
    'users: Mapped[List["User"]] = relationship("User", back_populates="institution", cascade="all, delete-orphan")',
    'users: Mapped[List["User"]] = relationship("User", back_populates="institution", cascade="all, delete-orphan")\n    batches: Mapped[List["Batch"]] = relationship("Batch", back_populates="institution", cascade="all, delete-orphan")'
)

# Also add import Batch if needed, or rely on string resolution
with open(r'backend\app\models\institution.py', 'w', encoding='utf-8') as f:
    f.write(text)
