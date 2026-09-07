import pathlib
import re

def fix_file(file_path):
    content = file_path.read_text(encoding='utf-8')
    def replacer(match):
        val = match.group(1).strip()
        return f'className="{val}"'
    
    fixed = re.sub(r'className=\s*([a-zA-Z0-9_\-\/\[\]]+)(?=[ >])', replacer, content)
    file_path.write_text(fixed, encoding='utf-8')

for p in pathlib.Path('frontend-next/src').rglob('*.tsx'):
    fix_file(p)
print('Quotes fixed successfully.')
