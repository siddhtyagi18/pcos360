import os
import re

hooks = ['useState', 'useEffect', 'useCallback', 'useMemo', 'useRef', 'useContext']
pattern = re.compile(r'\b(useState|useEffect|useCallback|useMemo|useRef|useContext)\b')

for root, _, files in os.walk('mobile/src'):
    for f in files:
        if f.endswith(('.js', '.jsx')):
            p = os.path.join(root, f)
            with open(p, 'r', encoding='utf-8') as fp:
                content = fp.read()
            react_import_match = re.search(r'import\s+[^;]*\{([^}]+)\}\s+from\s+[\'\"]react[\'\"]', content)
            imported_hooks = set()
            if react_import_match:
                imported_hooks = {h.strip() for h in react_import_match.group(1).split(',')}
            used_hooks = set(pattern.findall(content))
            missing = used_hooks - imported_hooks
            really_missing = set()
            for m in missing:
                # check if prefixed with React.
                stripped = re.sub(r'React\.' + m, '', content)
                if re.search(r'\b' + m + r'\b', stripped):
                    really_missing.add(m)
            if really_missing:
                print(f"{p}: missing {really_missing}")

