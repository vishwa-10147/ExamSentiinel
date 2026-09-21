with open('frontend/app/layout.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

import_stmt = 'import { SidebarProvider } from "@/contexts/SidebarContext";\n'
content = content.replace('import { AuthProvider }', import_stmt + 'import { AuthProvider }')
content = content.replace('<AuthProvider>', '<AuthProvider>\n          <SidebarProvider>')
content = content.replace('</AuthProvider>', '</SidebarProvider>\n        </AuthProvider>')

with open('frontend/app/layout.tsx', 'w', encoding='utf-8') as f:
    f.write(content)
print('Updated layout.tsx')
