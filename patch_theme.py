import sys

with open(r'frontend\app\layout.tsx', 'r') as f:
    text = f.read()

old_body = '''    <html lang="en">
      <body className="bg-slate-50 min-h-screen text-slate-900 antialiased font-sans">
        <AuthProvider>'''

new_body = '''    <html lang="en" suppressHydrationWarning>
      <body className="bg-slate-50 dark:bg-slate-900 min-h-screen text-slate-900 dark:text-slate-50 antialiased font-sans transition-colors duration-200">
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
          <AuthProvider>'''

text = text.replace(old_body, new_body)
text = text.replace('</AuthProvider>\n        <Toaster position="top-right" />\n        <CookieBanner />\n      </body>', '</AuthProvider>\n        <Toaster position="top-right" />\n        <CookieBanner />\n        </ThemeProvider>\n      </body>')

if 'ThemeProvider' not in text and 'import { ThemeProvider }' not in text:
    text = 'import { ThemeProvider } from "next-themes";\n' + text

with open(r'frontend\app\layout.tsx', 'w') as f:
    f.write(text)
