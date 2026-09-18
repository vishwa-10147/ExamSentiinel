import sys

with open(r'backend\tests\test_security.py', 'r') as f:
    text = f.read()

text = text.replace('create_access_token(candidate.id,', 'create_access_token({"sub": str(candidate.id)},')

with open(r'backend\tests\test_security.py', 'w') as f:
    f.write(text)
