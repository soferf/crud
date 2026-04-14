"""
Run once: python fix_bootstrap.py
Removes the corrupted Jinja2 content that was accidentally appended to bootstrap.py.
"""
import os

BASE = os.path.dirname(os.path.abspath(__file__))
bootstrap_path = os.path.join(BASE, 'bootstrap.py')

# Read the file
with open(bootstrap_path, 'r', encoding='utf-8') as f:
    content = f.read()

# The valid Python ends at the line with the last print statement
# Everything from the blank line + junk Jinja2 content onward is removed
CUTOFF = "print('  /produccion/nueva   - Registrar cosecha')"

idx = content.find(CUTOFF)
if idx == -1:
    print("ERROR: Could not find cutoff marker. bootstrap.py may already be fixed.")
else:
    clean = content[:idx + len(CUTOFF)] + '\n'
    with open(bootstrap_path, 'w', encoding='utf-8') as f:
        f.write(clean)
    print('fix_bootstrap.py: bootstrap.py truncated successfully.')
    print('bootstrap.py now ends at:')
    print(f'  {CUTOFF}')
    print('\nYou can now run: python bootstrap.py')
