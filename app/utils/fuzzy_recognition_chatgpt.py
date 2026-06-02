OCR_NORMALIZE = {
    'O': '0',
    'D': '0',
    'I': '1',
    'L': '1',
    'Z': '2',
    'S': '5',
    'B': '8'
}

def normalize(s):
    return ''.join(OCR_NORMALIZE.get(c, c) for c in s)
abs(len(o) - len(s)) <= 1

def prefix_match(a, b, k=3):
    return sum(a[i]==b[i] for i in range(min(k,len(a),len(b))))
from Levenshtein import distance
edit_score = 1 - distance(o, s) / max(len(o), len(s))

def positional_score(a, b):
    L = min(len(a), len(b))
    return sum(a[i]==b[i] for i in range(L)) / L
