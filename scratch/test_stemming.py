import re

def get_tokens_fixed(text: str) -> list[str]:
    if not text:
        return []
    text = re.sub(r'[^a-zA-Z0-9\s]', ' ', text.lower())
    raw_tokens = text.split()
    tokens = []
    for t in raw_tokens:
        if len(t) <= 2:
            continue
        stemmed = t
        if t.endswith('ies'):
            stemmed = t[:-3] + 'y'
        elif t.endswith('s') and not t.endswith('ss'):
            # Check if it's a special plural like -ches, -shes, -xes, -zes
            if t.endswith('es') and any(t.endswith(suffix) for suffix in ('shes', 'ches', 'xes', 'zes')):
                stemmed = t[:-2]
            else:
                stemmed = t[:-1]
        tokens.append(stemmed)
    return tokens

test_words = ['electrolytes', 'electrolyte', 'capsules', 'capsule', 'gummies', 'gummy', 'boxes', 'box', 'dishes', 'dish', 'passes', 'pass']
print("STEMMING TEST:")
for w in test_words:
    print(f"  '{w}' -> '{get_tokens_fixed(w)[0]}'")
