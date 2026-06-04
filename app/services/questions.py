import re
from collections import defaultdict

QUESTION_PATTERNS = [
    r'\?',
    r'\balgu[ée]m\s+sabe\b',
    r'\bcomo\s+faz\b',
    r'\bcomo\s+faço\b',
    r'\bcomo\s+fazer\b',
    r'\bo\s+que\s+[éeé]\b',
    r'\bqual\s+a\s+diferença\b',
    r'\bme\s+explica\b',
    r'\bquero\s+saber\b',
    r'\bqueria\s+saber\b',
    r'\bgostaria\s+de\s+saber\b',
    r'\bpor\s+que\b',
    r'\bporque\b',
    r'\bquando\b',
    r'\bonde\b',
    r'\bquem\b',
    r'\bqual\b',
    r'\bquais\b',
    r'\bquanto\b',
    r'\bquantos\b',
    r'\bposso\b',
    r'\bexiste\b',
    r'\btem\s+como\b',
    r'\bdá\s+pra\b',
    r'\bvocês?\s+(vão|vao|vai|irão|irao)\b',
    r'\bquando\s+(vai|será|sera|começa|comeca)\b',
    r'\balgu[ée]m\s+(sabe|pode|consegue|ajuda)\b',
    r'\bpoderiam?\s+me\b',
    r'\bvocês?\s+sabem\b',
    r'\bvocês?\s+têm\b',
    r'\bcad[êe]\b',
]


def is_question(text: str) -> bool:
    text_lower = text.lower().strip()
    for pattern in QUESTION_PATTERNS:
        if re.search(pattern, text_lower):
            return True
    return False


def tokenize(text: str) -> set[str]:
    return set(re.findall(r'\b\w+\b', text.lower()))


def jaccard_similarity(set1: set[str], set2: set[str]) -> float:
    if not set1 or not set2:
        return 0.0
    intersection = set1 & set2
    union = set1 | set2
    return len(intersection) / len(union)


def detect_questions(texts: list[str], min_length: int = 10) -> list[dict]:
    questions = [t for t in texts if len(t) >= min_length and is_question(t)]

    if not questions:
        return []

    groups: list[list] = []
    tokens_cache = {q: tokenize(q) for q in questions}
    assigned = set()

    for i, question in enumerate(questions):
        if i in assigned:
            continue
        q_tokens = tokens_cache[question]
        group = [question]
        assigned.add(i)
        for j in range(i + 1, len(questions)):
            if j in assigned:
                continue
            other_tokens = tokens_cache[questions[j]]
            sim = jaccard_similarity(q_tokens, other_tokens)
            if sim >= 0.5:
                group.append(questions[j])
                assigned.add(j)
        groups.append(group)

    result = []
    for group in groups:
        text_counts: dict[str, int] = defaultdict(int)
        for q in group:
            text_counts[q] += 1

        sorted_examples = sorted(text_counts.items(), key=lambda x: x[1], reverse=True)
        examples = [text for text, _ in sorted_examples[:3]]

        result.append({
            "text": group[0],
            "count": len(group),
            "examples": examples,
        })

    return result
