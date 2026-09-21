import os
import glob

def remove_bom(filepath):
    with open(filepath, 'rb') as f:
        content = f.read()
    if content.startswith(b'\xef\xbb\xbf'):
        with open(filepath, 'wb') as f:
            f.write(content[3:])
            print(f"Removed BOM from {filepath}")
    elif content.startswith(b'\xff\xfe'):
        # UTF-16 LE BOM - powershell default sometimes!
        content = content.decode('utf-16-le').encode('utf-8')
        with open(filepath, 'wb') as f:
            f.write(content)
            print(f"Converted UTF-16 LE to UTF-8 {filepath}")

for root, _, files in os.walk('frontend'):
    for file in files:
        if file.endswith('.tsx') or file.endswith('.ts'):
            remove_bom(os.path.join(root, file))
