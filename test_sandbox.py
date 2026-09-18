import sys
import os

sys.path.append(os.path.join(os.getcwd(), 'backend'))
from app.services.sandbox_service import sandbox_service

code = 'print("A" * 1024 * 1024 * 50)' # 50MB
try:
    res = sandbox_service.execute('python', code, '', 5.0, 128)
    print(f'Status: {res.status}, stdout len: {len(res.stdout)}')
except Exception as e:
    print('Exception:', e)
