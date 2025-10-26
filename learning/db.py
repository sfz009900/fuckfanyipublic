import os
import json
import time
import hashlib
from typing import List, Dict, Any, Optional


class LearningDB:
    """A lightweight JSON store for learning items and reviews.

    Structure:
    - items: dict[id] -> {id, term, type, hint, translation, contexts, created_at,
                          ease, interval_sec, reps, lapses, due_ts}
    - reviews: list of {id, ts, grade}
    """

    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)
        self.items_path = os.path.join(self.base_dir, 'items.json')
        self.reviews_path = os.path.join(self.base_dir, 'reviews.json')
        self._items: Dict[str, Dict[str, Any]] = {}
        self._reviews: List[Dict[str, Any]] = []
        self._load()

    @staticmethod
    def make_id(term: str, type_: str) -> str:
        key = f"{type_.lower()}|{(term or '').strip().lower()}".encode('utf-8')
        return hashlib.sha1(key).hexdigest()

    def _load(self):
        try:
            if os.path.exists(self.items_path):
                with open(self.items_path, 'r', encoding='utf-8') as f:
                    self._items = json.load(f)
            if os.path.exists(self.reviews_path):
                with open(self.reviews_path, 'r', encoding='utf-8') as f:
                    self._reviews = json.load(f)
        except Exception:
            # Corruption fallback
            self._items = {}
            self._reviews = []

    def _save(self):
        tmp_items = self.items_path + '.tmp'
        tmp_reviews = self.reviews_path + '.tmp'
        with open(tmp_items, 'w', encoding='utf-8') as f:
            json.dump(self._items, f, ensure_ascii=False, indent=2)
        with open(tmp_reviews, 'w', encoding='utf-8') as f:
            json.dump(self._reviews, f, ensure_ascii=False, indent=2)
        os.replace(tmp_items, self.items_path)
        os.replace(tmp_reviews, self.reviews_path)

    def upsert_item(self, *, term: str, type_: str, hint: str = '', translation: str = '',
                    context: Optional[Dict[str, Any]] = None) -> str:
        item_id = self.make_id(term, type_)
        now = int(time.time())
        item = self._items.get(item_id)
        if item is None:
            item = {
                'id': item_id,
                'term': term,
                'type': type_,
                'hint': hint,
                'translation': translation,
                'contexts': [],
                'created_at': now,
                'ease': 2.5,
                'interval_sec': 0,
                'reps': 0,
                'lapses': 0,
                'due_ts': now,  # ready to learn
            }
            self._items[item_id] = item
        # merge context
        if context:
            try:
                # dedupe by content hash of context
                ctx_key = json.dumps(context, ensure_ascii=False, sort_keys=True)
                existing = {json.dumps(c, ensure_ascii=False, sort_keys=True) for c in item.get('contexts', [])}
                if ctx_key not in existing:
                    item.setdefault('contexts', []).append(context)
            except Exception:
                pass
        # update hint/translation if empty
        if hint and not item.get('hint'):
            item['hint'] = hint
        if translation and not item.get('translation'):
            item['translation'] = translation
        self._save()
        return item_id

    def get_due_items(self, limit: int = 5) -> List[Dict[str, Any]]:
        now = int(time.time())
        items = [v for v in self._items.values() if int(v.get('due_ts', now)) <= now]
        # prioritize least reviewed and with contexts
        items.sort(key=lambda x: (x.get('reps', 0), -len(x.get('contexts', [])), x.get('created_at', 0)))
        return items[:limit]

    def get_recent_new_items(self, limit: int = 5) -> List[Dict[str, Any]]:
        items = sorted(self._items.values(), key=lambda x: x.get('created_at', 0), reverse=True)
        fresh = [i for i in items if i.get('reps', 0) == 0]
        return fresh[:limit]

    def get_items_by_ids(self, ids: List[str]) -> List[Dict[str, Any]]:
        return [self._items[i] for i in ids if i in self._items]

    def update_item_schedule(self, item_id: str, *, ease: float, interval_sec: int, reps: int, lapses: int):
        item = self._items.get(item_id)
        if not item:
            return
        item['ease'] = ease
        item['interval_sec'] = int(interval_sec)
        item['reps'] = int(reps)
        item['lapses'] = int(lapses)
        item['due_ts'] = int(time.time()) + int(interval_sec)
        self._save()

    def log_review(self, item_id: str, grade: int):
        self._reviews.append({'id': item_id, 'ts': int(time.time()), 'grade': int(grade)})
        self._save()

