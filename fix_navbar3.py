with open('frontend/components/Navbar.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('</Link>', '</Link>\\n        </div>')

with open('frontend/components/Navbar.tsx', 'w', encoding='utf-8') as f:
    f.write(text)
print('Fixed Navbar closing div')
