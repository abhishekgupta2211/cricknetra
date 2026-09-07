import pathlib

def clean_file(path):
    text = path.read_text(encoding='utf-8')
    # Remove any stray non-standard spaces or carriage returns
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = text.replace('\u00a0', ' ')
    path.write_text(text, encoding='utf-8')

for p in pathlib.Path('frontend-next/src').rglob('*.tsx'):
    clean_file(p)

print('Whitespace cleaned.')
