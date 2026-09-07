import pathlib
import re

def fix(p):
    c = p.read_text(encoding='utf-8')
    # Loop regex until no split quotes remain
    for _ in range(5):
        c = re.sub(r'className="([^"]*)"\s+([a-zA-Z0-9_\-\/\[\]]+)', r'className="\1 \2"', c)
    p.write_text(c, encoding='utf-8')

for p in pathlib.Path('frontend-next/src/app').rglob('*.tsx'):
    fix(p)

print('Split className attributes merged successfully.')
