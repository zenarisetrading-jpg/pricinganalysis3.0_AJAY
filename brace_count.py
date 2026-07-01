import re
with open('script0.js', 'r', encoding='utf-8') as f:
    text = f.read()

# Naive remove strings and comments
text = re.sub(r'//.*', '', text)
text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
text = re.sub(r'`[^`]*`', '\"\"', text, flags=re.DOTALL)
text = re.sub(r"'[^']*'", '\"\"', text)
text = re.sub(r'"[^"]*"', '\"\"', text)

print('Open (: ', text.count('('))
print('Close ): ', text.count(')'))
print('Open {: ', text.count('{'))
print('Close }: ', text.count('}'))
