import re

path = r'c:/Users/Office/RAG/ui/js/languages.js'

with open(path, encoding='utf-8') as f:
    content = f.read()

# Replace all brandName values with MA3AK
content = re.sub(r"brandName:\s*'[^']*'", "brandName: 'MA3AK'", content)
# Replace all brandSub values with RAG System
content = re.sub(r"brandSub:\s*'[^']*'", "brandSub:  'RAG System'", content)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

bn = len(re.findall(r"brandName: 'MA3AK'", content))
bs = len(re.findall(r"brandSub:  'RAG System'", content))
print(f"brandName updated: {bn} languages")
print(f"brandSub updated:  {bs} languages")
