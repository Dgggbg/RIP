import re

path = r'c:/Users/Office/RAG/ui/js/languages.js'

with open(path, encoding='utf-8') as f:
    content = f.read()

new_content = re.sub(r"wTitle:\s*'[^']*'", "wTitle:    'MA3AK'", content)
count = new_content.count("'MA3AK'")

with open(path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print(f"Done! MA3AK appears {count} times now.")
