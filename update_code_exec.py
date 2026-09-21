import re

filepath = 'backend/app/api/code_execution.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('sandbox_service.execute(', 'await sandbox_service.execute_async(')
# Remove SandboxUnavailableError as we don't raise it anymore
content = content.replace('from app.services.sandbox_service import SandboxUnavailableError, sandbox_service', 'from app.services.sandbox_service import sandbox_service')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated code_execution.py")
