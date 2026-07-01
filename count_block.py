import re
with open('dashboard/price_benchmarking.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()
chunk = ''.join(lines[3092:3287])

# Simple character-level tokenizer to avoid regex parsing issues
chars = []
in_string = False
string_char = ''
in_comment = False
in_multiline = False

i = 0
while i < len(chunk):
    c = chunk[i]
    if in_string:
        if c == '\\':
            i += 1
        elif c == string_char:
            in_string = False
    elif in_comment:
        if c == '\n':
            in_comment = False
    elif in_multiline:
        if c == '*' and i+1 < len(chunk) and chunk[i+1] == '/':
            in_multiline = False
            i += 1
    else:
        if c == '/' and i+1 < len(chunk) and chunk[i+1] == '/':
            in_comment = True
            i += 1
        elif c == '/' and i+1 < len(chunk) and chunk[i+1] == '*':
            in_multiline = True
            i += 1
        elif c in "'\"`":
            in_string = True
            string_char = c
        elif c in "(){}[]":
            chars.append((c, i))
    i += 1

stack = []
for c, idx in chars:
    if c in '({[':
        stack.append((c, idx))
    elif c in ')}]':
        if not stack:
            print(f'Unmatched {c} at string index {idx}')
            lines_so_far = chunk[:idx].count('\n') + 1
            print(f'Line relative to block: {lines_so_far}')
            exit()
        top, top_idx = stack.pop()
        if (top == '(' and c != ')') or (top == '{' and c != '}') or (top == '[' and c != ']'):
            print(f'Mismatched {c} at string index {idx}. Expected match for {top} at {top_idx}')
            lines_so_far = chunk[:idx].count('\n') + 1
            print(f'Line relative to block: {lines_so_far}')
            exit()

if stack:
    for c, idx in stack:
        print(f'Unclosed {c} at string index {idx}')
        lines_so_far = chunk[:idx].count('\n') + 1
        print(f'Line relative to block: {lines_so_far}')
else:
    print('All matched perfectly!')
