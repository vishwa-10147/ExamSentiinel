import sys

with open(r'backend\app\models\institution.py', 'r') as f:
    text = f.read()

new_fields = '''    settings: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Monetization & Billing
    stripe_customer_id: Mapped[str] = mapped_column(String(255), nullable=True, unique=True, index=True)
    subscription_tier: Mapped[str] = mapped_column(String(64), default="free", nullable=False)
    subscription_status: Mapped[str] = mapped_column(String(64), default="active", nullable=False)'''

text = text.replace('    settings: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)', new_fields)

with open(r'backend\app\models\institution.py', 'w') as f:
    f.write(text)
