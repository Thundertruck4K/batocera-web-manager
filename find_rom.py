import re
p = r'C:\Users\folk3\Downloads\batocera_web\templates\index.html'
with open(p, encoding='utf-8', errors='replace') as f:
    s = f.read()
# search for rom-related IDs
for m in re.finditer(r'id=["\']([^"\']*rom[^"\']*)["\']', s, re.I):
    print(m.group(1))
    break
else:
    print('no')