with open('frontend/components/Navbar.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('        </div>\n      </div>\n    </header>', '        </div>\n        </div>\n      </div>\n    </header>')
with open('frontend/components/Navbar.tsx', 'w', encoding='utf-8') as f:
    f.write(text)
