from typing import Optional, Dict


def acrostic(phrase: str) -> str:
    parts = [p for p in phrase.split() if p]
    if not parts:
        return ''
    letters = ''.join(w[0].upper() for w in parts)
    return f"首字母：{letters}"


def build_mnemonic(term: str, type_: str, translation: Optional[str] = None, context: Optional[Dict] = None) -> str:
    """Return a short, playful mnemonic in Chinese without external calls."""
    cn = translation or ''
    ctx_hint = ''
    if context:
        # Use a tiny slice of source text if available
        src = (context.get('source_text') or '')[:40]
        if src:
            ctx_hint = f"｜情境：{src}"

    if type_ == 'phrase' and ' ' in term:
        return f"把它想成一个动作块：{term} → {cn}。{acrostic(term)} {ctx_hint}".strip()
    else:
        return f"画面记忆：想象“{term}”=“{cn}”，在脑中快速闪过一幕。{ctx_hint}".strip()

