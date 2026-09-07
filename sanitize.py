import pathlib
import re

def sanitize_tsx(path):
    text = path.read_text(encoding='utf-8')
    # Fix self-closing tag syntax like /"> -> " />
    text = re.sub(r'/"\s*>', '" />', text)
    # Fix standalone unquoted attributes
    text = re.sub(r'(\s+)([a-zA-Z0-9_\-]+)=([^\s">\']+)(\s+|>|/>)', r'\1\2="\3"\4', text)
    path.write_text(text, encoding='utf-8')

for p in pathlib.Path('frontend-next/src').rglob('*.tsx'):
    sanitize_tsx(p)

print('Sanitization finished.')
