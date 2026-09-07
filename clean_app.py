import pathlib
import re

def fix_jsx_file(p):
    content = p.read_text(encoding='utf-8')
    lines = content.splitlines()
    new_lines = []
    for line in lines:
        if 'className=' in line:
            # Matches className= string until > or end of tag or next attribute
            # E.g. className= flex flex-col items-center -> className="flex flex-col items-center"
            def fix_line(m):
                full_val = m.group(1).strip()
                # If already wrapped in quotes or curly braces, return unchanged
                if full_val.startswith('"') or full_val.startswith("'") or full_val.startswith('{'):
                    return m.group(0)
                # Remove any existing broken quotes inside
                clean_val = full_val.replace('"', '').replace("'", '')
                return f'className="{clean_val}"'
            
            line = re.sub(r'className=\s*([^>]+?)(?=\s+[a-zA-Z0-9_\-]+=|/?>)', fix_line, line)
        new_lines.append(line)
    p.write_text('\n'.join(new_lines), encoding='utf-8')

for p in pathlib.Path('frontend-next/src/app').rglob('*.tsx'):
    fix_jsx_file(p)

print("Comprehensive JSX attribute fix complete.")
