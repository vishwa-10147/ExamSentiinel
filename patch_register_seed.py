import re

# 1. Patch register page
with open('frontend/app/auth/register/page.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace(
    'await fetch("http://localhost:8000/api/auth/register",',
    'await fetch((process.env.NEXT_PUBLIC_API_URL || (process.env.NODE_ENV === "production" ? "https://examsentinel-backend.onrender.com" : "http://localhost:8000")) + "/api/auth/register",'
)

with open('frontend/app/auth/register/page.tsx', 'w', encoding='utf-8') as f:
    f.write(text)

# 2. Patch backend Dockerfile to run seed_admin.py
with open('backend/Dockerfile', 'r', encoding='utf-8') as f:
    dockerfile = f.read()

dockerfile = dockerfile.replace(
    'python -m alembic upgrade head && uvicorn',
    'python -m alembic upgrade head && python seed_admin.py && uvicorn'
)

with open('backend/Dockerfile', 'w', encoding='utf-8') as f:
    f.write(dockerfile)
