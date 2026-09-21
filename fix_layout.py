import re

# 1. Update Login Page
with open('frontend/app/auth/login/page.tsx', 'r', encoding='utf-8') as f:
    text1 = f.read()

old_login_header = '''<div className="text-center">
          <Image src="/logo.png" alt="ExamSentinel Logo" width={48} height={48}  className="mx-auto h-20 w-auto object-contain drop-shadow-sm" />
          <h2 className="mt-4 text-2xl font-bold tracking-tight text-slate-900">
            {requires2fa ? "Two-Factor Authentication" : "Sign in to ExamSentinel"}
          </h2>'''

new_login_header = '''<div className="text-center">
          <div className="flex items-center justify-center gap-3">
            <Image src="/logo.png" alt="ExamSentinel Logo" width={40} height={40} className="h-10 w-auto object-contain drop-shadow-sm" />
            <h2 className="text-2xl font-bold tracking-tight text-slate-900">
              {requires2fa ? "Two-Factor Auth" : "Sign in"}
            </h2>
          </div>'''

text1 = text1.replace(old_login_header, new_login_header)

with open('frontend/app/auth/login/page.tsx', 'w', encoding='utf-8') as f:
    f.write(text1)

# 2. Update Register Page
with open('frontend/app/auth/register/page.tsx', 'r', encoding='utf-8') as f:
    text2 = f.read()

old_register_header = '''<div className="text-center">
          <Image src="/logo.png" alt="ExamSentinel Logo" width={48} height={48} style={{ width: "auto", height: "auto" }} className="mx-auto drop-shadow-sm" />
          <h2 className="mt-4 text-2xl font-bold tracking-tight text-slate-900">
            Create an Account
          </h2>'''

new_register_header = '''<div className="text-center">
          <div className="flex items-center justify-center gap-3">
            <Image src="/logo.png" alt="ExamSentinel Logo" width={40} height={40} className="h-10 w-auto object-contain drop-shadow-sm" />
            <h2 className="text-2xl font-bold tracking-tight text-slate-900">
              Create an Account
            </h2>
          </div>'''

text2 = text2.replace(old_register_header, new_register_header)

with open('frontend/app/auth/register/page.tsx', 'w', encoding='utf-8') as f:
    f.write(text2)
