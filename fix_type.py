with open('frontend/app/admin/questions/page.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('const data = await apiClient.get("/api/questions");', 'const data = await apiClient.get<Question[]>("/api/questions");')

with open('frontend/app/admin/questions/page.tsx', 'w', encoding='utf-8') as f:
    f.write(text)
