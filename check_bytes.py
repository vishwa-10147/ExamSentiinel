with open('frontend/app/admin/questions/page.tsx', 'rb') as f:
    text = f.read()

idx = text.find(b'return (\n    <div className="flex-1')
if idx == -1:
    idx = text.find(b'return (\r\n    <div className="flex-1')

if idx != -1:
    print([hex(c) for c in text[idx-10:idx+20]])
else:
    print("Not found")
