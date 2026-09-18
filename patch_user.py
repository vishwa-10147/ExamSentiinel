import sys

with open(r'backend\app\models\user.py', 'r', encoding='utf-8') as f:
    text = f.read()

insert = '''    institution_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=True, index=True
    )
    
    # Batch & Roll Number
    roll_number: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    batch_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("batches.id", ondelete="SET NULL"), nullable=True, index=True
    )
    batch: Mapped[Optional["Batch"]] = relationship("Batch", back_populates="users")
'''

text = text.replace(
    '''    institution_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=True, index=True
    )''',
    insert
)

with open(r'backend\app\models\user.py', 'w', encoding='utf-8') as f:
    f.write(text)
