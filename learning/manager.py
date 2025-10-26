import os
import threading
from typing import List, Dict, Callable, Optional

from config_manager import config
from .db import LearningDB
from .scheduler import SM2State, next_review
from .extract import extract_candidates
from .mnemonic import build_mnemonic


class LearningManager:
    """Coordinator for extraction, storage, scheduling and gameplay data."""

    def __init__(self, project_root: str, translate_fn: Optional[Callable[[str], Optional[str]]] = None):
        data_dir = os.path.join(project_root, 'learning', 'data')
        os.makedirs(data_dir, exist_ok=True)
        self.db = LearningDB(data_dir)
        self.translate_fn = translate_fn
        # capture session mapping: capture_id -> [item_ids]
        self._latest_capture_id: Optional[str] = None
        self._capture_to_items: Dict[str, List[str]] = {}
        # Cache full original and translation text per capture session
        self._capture_texts: Dict[str, str] = {}
        self._capture_translations: Dict[str, str] = {}

    # ————————— Ingestion —————————
    def ingest(self, source_text: str, translated_text: Optional[str] = None, context: Optional[Dict] = None,
               top_k: int = 8, async_mode: bool = True):
        """Extract candidates and upsert as learnable items.

        If async_mode, it runs in background.
        """
        if not source_text:
            return

        def _job():
            cands = extract_candidates(source_text, top_k=top_k)
            cap_id = None
            if isinstance(context, dict):
                cap_id = str(context.get('capture_id') or '') or None
                if cap_id:
                    # cache full texts for this capture (used by overlay UI)
                    self._capture_texts[cap_id] = source_text
                    if translated_text:
                        self._capture_translations[cap_id] = translated_text
            for c in cands:
                term = c['term']
                type_ = c['type']
                # Fast ingest: skip network translation, fill hints later in game prep
                zh = ''
                hint = build_mnemonic(term, type_, zh, context)
                ctx = context or {}
                if source_text and not ctx.get('source_text'):
                    ctx['source_text'] = source_text[:200]
                if translated_text and not ctx.get('translated_text'):
                    ctx['translated_text'] = translated_text[:200]
                item_id = self.db.upsert_item(term=term, type_=type_, hint=hint, translation=zh, context=ctx)
                # record under this capture session
                if cap_id:
                    lst = self._capture_to_items.setdefault(cap_id, [])
                    if item_id not in lst:
                        lst.append(item_id)

        if async_mode:
            threading.Thread(target=_job, daemon=True).start()
        else:
            _job()

    # ————————— Capture sessions —————————
    def begin_capture(self, capture_id: str):
        self._latest_capture_id = str(capture_id)
        # reset list for this capture
        self._capture_to_items[self._latest_capture_id] = []

    # ————————— Scheduling —————————
    def due_items(self, limit: int = 5) -> List[Dict]:
        items = self.db.get_due_items(limit=limit)
        if len(items) < limit:
            items += [i for i in self.db.get_recent_new_items(limit=limit - len(items)) if i not in items]
        return items[:limit]

    def review(self, item_id: str, grade: int):
        item_list = self.db.get_items_by_ids([item_id])
        if not item_list:
            return
        item = item_list[0]
        state = SM2State(
            ease=float(item.get('ease', 2.5)),
            interval_sec=int(item.get('interval_sec', 0)),
            reps=int(item.get('reps', 0)),
            lapses=int(item.get('lapses', 0)),
        )
        new_state = next_review(state, grade)
        self.db.update_item_schedule(item_id, ease=new_state.ease, interval_sec=new_state.interval_sec,
                                     reps=new_state.reps, lapses=new_state.lapses)
        self.db.log_review(item_id, grade)

    # ————————— Game data prep —————————
    @staticmethod
    def _is_chinese(s: str) -> bool:
        if not s:
            return False
        import re
        return re.search(r"[\u4e00-\u9fff]", s) is not None

    @staticmethod
    def _shorten_hint(hint: str, max_len: int = 16) -> str:
        hint = hint or ''
        # prefer first clause
        for sep in ['；', '。', '，', ';', '.', ',']:
            if sep in hint:
                hint = hint.split(sep, 1)[0]
        return hint[:max_len]

    def _gloss(self, term: str, fallback: str = '') -> str:
        # Try translate_fn first for a concise hint
        zh = ''
        if callable(self.translate_fn):
            try:
                zh = self.translate_fn(term) or ''
            except Exception:
                zh = ''
        zh = zh or fallback or term
        # sanitize and prefer Chinese
        zh = self._shorten_hint(zh)
        return zh

    def prepare_game_items(self, limit: int = 5, current_only: bool = False) -> List[Dict]:
        """Return enriched items with unique, readable Chinese hints in key 'game_hint'.

        Preference: terms that actually appear in recent contexts and longer phrases.
        """
        if current_only and self._latest_capture_id and self._latest_capture_id in self._capture_to_items:
            ids = self._capture_to_items.get(self._latest_capture_id, [])
            raw = self.db.get_items_by_ids(ids)
            # Augment if too few using cached source text
            if len(raw) < limit:
                src = self._capture_texts.get(self._latest_capture_id, '')
                if src:
                    # Try to extract more synchronously
                    try:
                        self.ingest(src, translated_text=None, context={'capture_id': self._latest_capture_id}, top_k=max(limit*2, 12), async_mode=False)
                        ids = self._capture_to_items.get(self._latest_capture_id, [])
                        raw = self.db.get_items_by_ids(ids)
                    except Exception:
                        pass
            raw = raw[:limit]
        else:
            raw = self.due_items(limit=max(limit * 2, 6))
        # score by: appears in any context + length weight
        def _score(it: Dict) -> int:
            term = (it.get('term') or '').lower()
            score = len(term)
            contexts = it.get('contexts') or []
            for c in contexts:
                src = (c.get('source_text') or '').lower()
                if term and term in src:
                    score += 10
            return score
        items = sorted(raw, key=_score, reverse=True)[:limit]
        hints_seen = set()
        enriched: List[Dict] = []
        for idx, it in enumerate(items, 1):
            base_hint = it.get('translation') or it.get('hint') or ''
            zh = self._gloss(it.get('term',''), base_hint)
            # ensure Chinese presence; if not, append minimal cue
            if not self._is_chinese(zh):
                zh = f"{zh}（{it.get('term','')}）"
            zh = self._shorten_hint(zh)
            # ensure uniqueness
            unique = zh
            if unique in hints_seen:
                # append small cue from acrostic letters
                from .mnemonic import acrostic
                cue = acrostic(it.get('term','')).replace('首字母：','') or str(idx)
                unique = f"{zh}·{cue}"
            hints_seen.add(unique)
            new_it = dict(it)
            new_it['game_hint'] = unique
            enriched.append(new_it)
        return enriched
