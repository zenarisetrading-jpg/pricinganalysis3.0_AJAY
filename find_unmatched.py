import re

with open('script0.js', 'r', encoding='utf-8') as f:
    text = f.read()

# Keep a map of indices for accurate line numbers
class CharTracker:
    def __init__(self, char, index):
        self.char = char
        self.index = index

chars = []
in_string = False
string_char = ''
in_comment = False
in_multiline = False

i = 0
while i < len(text):
    c = text[i]
    if in_string:
        if c == '\\':
            i += 1
        elif c == string_char:
            in_string = False
    elif in_comment:
        if c == '\n':
            in_comment = False
    elif in_multiline:
        if c == '*' and i+1 < len(text) and text[i+1] == '/':
            in_multiline = False
            i += 1
    else:
        if c == '/' and i+1 < len(text) and text[i+1] == '/':
            in_comment = True
            i += 1
        elif c == '/' and i+1 < len(text) and text[i+1] == '*':
            in_multiline = True
            i += 1
        elif c in "'\"`":
            in_string = True
            string_char = c
        elif c in "(){}[]":
            chars.append(CharTracker(c, i))
    i += 1

stack = []
for ct in chars:
    c = ct.char
    idx = ct.index
    if c in '({[':
        stack.append(ct)
    elif c in ')}]':
        if not stack:
            print(f'Unmatched {c} at string index {idx}')
            lines = text[:idx].count('\n') + 1
            print(f'Line: {lines}')
            exit()
        top = stack.pop()
        if (top.char == '(' and c != ')') or (top.char == '{' and c != '}') or (top.char == '[' and c != ']'):
            print(f'Mismatched {c} at string index {idx}. Expected match for {top.char} at {top.index}')
            lines = text[:idx].count('\n') + 1
            print(f'Line: {lines}')
            exit()

if stack:
    for ct in stack:
        print(f'Unclosed {ct.char} at string index {ct.index}')
        lines = text[:ct.index].count('\n') + 1
        print(f'Line: {lines}')
