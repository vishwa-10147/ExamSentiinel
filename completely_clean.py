def fix_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()

    # Navbar
    if 'Navbar.tsx' in filepath:
        text = text.replace('</Link>\n        </div>\n          </div>', '</Link>\n        </div>')
        if '<div className="flex items-center gap-4">' in text and '</Link>\n        </div>' not in text:
             text = text.replace('</Link>', '</Link>\n        </div>')
             
    # Questions page missing closing tag because of some earlier script? No, 'div' issue.
    # We will just git checkout it from origin/main.
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(text)

import os
os.system("git checkout origin/main frontend/app/admin/questions/page.tsx")
os.system("git checkout origin/main frontend/components/Navbar.tsx")
os.system("git checkout origin/main frontend/app/exam/[id]/lab/page.tsx")
os.system("git checkout origin/main frontend/app/candidate/practice/page.tsx")

import subprocess
subprocess.run(["python", "the_ultimate_fix.py"])

with open('frontend/app/exam/[id]/lab/page.tsx', 'r', encoding='utf-8') as f:
    lab = f.read()
lab = lab.replace('toast.error(Proctoring Alert: );', 'toast.error(`Proctoring Alert: ${eventType}`);')
with open('frontend/app/exam/[id]/lab/page.tsx', 'w', encoding='utf-8') as f:
    f.write(lab)

with open('frontend/components/Navbar.tsx', 'r', encoding='utf-8') as f:
    nav = f.read()
nav = nav.replace('</Link>\n          </div>', '</Link>\n        </div>\n          </div>')
with open('frontend/components/Navbar.tsx', 'w', encoding='utf-8') as f:
    f.write(nav)
