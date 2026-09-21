import re

with open('frontend/services/apiClient.ts', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace(
    'process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"',
    'process.env.NEXT_PUBLIC_API_URL || (process.env.NODE_ENV === "production" ? "https://examsentinel-backend.onrender.com" : "http://localhost:8000")'
)

with open('frontend/services/apiClient.ts', 'w', encoding='utf-8') as f:
    f.write(text)
