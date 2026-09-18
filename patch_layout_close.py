import sys

with open(r'frontend\app\layout.tsx', 'r') as f:
    text = f.read()

old_end = '''        </AuthProvider>
        <CookieBanner />
        <Toaster position="top-right" />
      </body>'''

new_end = '''        </AuthProvider>
        <CookieBanner />
        <Toaster position="top-right" />
        </ThemeProvider>
      </body>'''

text = text.replace(old_end, new_end)

with open(r'frontend\app\layout.tsx', 'w') as f:
    f.write(text)
