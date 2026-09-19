import sys

with open(r'backend\app\api\imports.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace(
    '''            db.add(user)
            imported_count += 1''',
    '''            db.add(user)
            imported_count += 1
            
            from app.services.email_service import email_service
            email_service.send_welcome_email(user.email, user.full_name, "Student123!")'''
)

with open(r'backend\app\api\imports.py', 'w', encoding='utf-8') as f:
    f.write(text)
