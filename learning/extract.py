import re
from collections import Counter
from typing import List, Dict


_STOP = {
    'a','an','the','and','or','but','if','then','so','of','in','on','at','to','for','from',
    'with','as','by','is','are','was','were','be','been','being','that','this','these','those',
    'it','its','into','over','under','about','than','not','no','do','does','did','done','can',
    'could','should','would','may','might','will','shall','you','we','they','i','he','she','them',
    'his','her','their','our','your','my','me','us','him','who','whom','which','what','when','where','why','how'
}

_PHRASAL_VERBS = {
    'set up','pick up','turn on','turn off','look up','look into','get over','run into',
    'break down','carry on','figure out','find out','come up with','put off','put up with',
}

_COMMON_SUFFIXES = ('tion','sion','ment','ness','able','ible','less','ful','wise','ship','ward','ance','ence')


def _tokens(text: str) -> List[str]:
    return re.findall(r"[A-Za-z][A-Za-z\-']+", text)


def extract_candidates(text: str, top_k: int = 10) -> List[Dict]:
    """Extract lightweight candidates: words + common phrasal verbs + salient bigrams."""
    if not text:
        return []

    # Phrasal verbs
    lowered = re.sub(r"\s+", " ", text.strip()).lower()
    phrases = []
    for pv in _PHRASAL_VERBS:
        if pv in lowered:
            phrases.append({'type': 'phrase', 'term': pv})

    # Words & bigrams
    toks = [t.lower() for t in _tokens(text)]
    # prefer longer, derivational suffix, and hyphenated compounds
    toks = [t for t in toks if t not in _STOP and (len(t) >= 5 or '-' in t or t.endswith(_COMMON_SUFFIXES))]
    counts = Counter(toks)

    # Bigrams (heuristic: frequent and non-stopword)
    bigrams = []
    for a, b in zip(toks, toks[1:]):
        if a in _STOP or b in _STOP:
            continue
        if len(a) <= 3 and len(b) <= 3:
            continue
        bigrams.append(f"{a} {b}")
    bi_counts = Counter(bigrams)

    # Rank: freq * (length + suffix bonus)
    def _wscore(wc):
        w, c = wc
        bonus = 1.0 + (0.5 if '-' in w else 0.0) + (0.3 if w.endswith(_COMMON_SUFFIXES) else 0.0)
        return c * (3 + len(w) * 0.2) * bonus
    word_rank = sorted(counts.items(), key=_wscore, reverse=True)
    bigram_rank = sorted(bi_counts.items(), key=lambda x: (x[1] * 6), reverse=True)

    results: List[Dict] = []
    # mix: 40% words, 40% bigrams, 20% phrasal
    n_words = max(2, top_k // 2)
    n_bis = max(2, top_k // 2)
    for w, _ in word_rank[:n_words]:
        results.append({'type': 'word', 'term': w})
    for bg, _ in bigram_rank[:n_bis]:
        if bg in _PHRASAL_VERBS:
            continue
        results.append({'type': 'phrase', 'term': bg})
    # append detected phrasal verbs
    results.extend(phrases)

    # Deduplicate by term
    seen = set()
    uniq = []
    for r in results:
        if r['term'] not in seen:
            seen.add(r['term'])
            uniq.append(r)

    # Optional: spaCy chunking if available
    try:
        import spacy  # type: ignore
        nlp = spacy.blank('en') if not hasattr(spacy, 'load') else None
        # If spaCy model not available, skip heavy call
    except Exception:
        nlp = None

    return uniq[:top_k]
