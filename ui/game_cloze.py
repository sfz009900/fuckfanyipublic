from __future__ import annotations

import re
import html
from typing import List, Dict, Callable, Optional
import string

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QWidget, QLineEdit, QMessageBox, QProgressBar
)

def _word_boundary_pattern(term: str) -> re.Pattern:
    # Use word boundaries if the term looks like a word; otherwise fall back to plain escape
    if re.match(r"^[A-Za-z][A-Za-z\-']*[A-Za-z]$", term or ""):
        pat = rf"\b{re.escape(term)}\b"
    else:
        pat = re.escape(term or "")
    return re.compile(pat, flags=re.IGNORECASE)


def make_cloze(sentence: str, answer: str) -> str:
    """Mask the first occurrence of answer, preserving punctuation and casing.

    - Prefer word-boundary match for English tokens
    - If not found, try a non-boundary fallback
    - If multiple occurrences exist, mask only the first
    """
    if not sentence or not answer:
        return sentence
    pat = _word_boundary_pattern(answer)
    out, n = pat.subn('____', sentence, count=1)
    if n == 0:
        pat2 = re.compile(re.escape(answer), flags=re.IGNORECASE)
        out = pat2.sub('____', sentence, count=1)
    return out


def _levenshtein(a: str, b: str) -> int:
    a = a or ""; b = b or ""
    la, lb = len(a), len(b)
    if la == 0:
        return lb
    if lb == 0:
        return la
    dp = list(range(lb + 1))
    for i, ca in enumerate(a, 1):
        prev = dp[0]
        dp[0] = i
        for j, cb in enumerate(b, 1):
            cur = dp[j]
            cost = 0 if ca == cb else 1
            dp[j] = min(dp[j] + 1, dp[j - 1] + 1, prev + cost)
            prev = cur
    return dp[-1]


def _strip_edges(s: str) -> str:
    if not s:
        return s
    left, right = 0, len(s)
    P = set(string.punctuation + "“”‘’")
    while left < right and s[left] in P:
        left += 1
    while right > left and s[right - 1] in P:
        right -= 1
    return s[left:right]


def _is_close_match(guess: str, answer: str) -> bool:
    g = (guess or '').strip().lower()
    a = (answer or '').strip().lower()
    if not g or not a:
        return False
    # fast path exact
    if g == a:
        return True
    # strip trivial punctuation from edges
    g = _strip_edges(g)
    a = _strip_edges(a)
    if g == a:
        return True
    # minor typos tolerance
    dist = _levenshtein(g, a)
    if len(a) <= 5:
        return dist <= 1
    return dist <= max(2, len(a) // 6)


class GameCloze(QDialog):
    """Cloze burst: type the missing word/phrase from the sentence."""

    def __init__(self, items: List[Dict], on_finish: Optional[Callable[[List[Dict]], None]] = None,
                 rounds: int = 3, parent=None, font_px: int = 16, high_contrast: bool = True,
                 per_item_seconds: int = 15):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        try:
            self.setAttribute(Qt.WA_DeleteOnClose)
        except Exception:
            pass
        self.items = items[:max(1, rounds)]
        self.on_finish = on_finish
        self.font_px = max(12, min(int(font_px), 24))
        self.high_contrast = bool(high_contrast)
        self.index = 0
        self.results: List[Dict] = []
        self.attempts = 0
        self.per_item_seconds = max(8, min(int(per_item_seconds), 60))
        self.per_item_ms = self.per_item_seconds * 1000
        self.deadline_ms = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.total_rounds = len(self.items)
        self.correct_count = 0
        self.skip_count = 0
        self.hint_count = 0
        self._hint_used = False
        self.current_sentence_raw = ""
        self.current_answer = ""
        self.current_translation = ""
        self._round_active = False

        self._build_ui()
        self._load_round()

    def _build_ui(self):
        self.setMinimumSize(720, 320)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)
        outer.setSpacing(0)

        card = QWidget()
        card.setObjectName("cloze_card")
        card.setStyleSheet("QWidget#cloze_card{background:#ffffff;border-radius:18px;}")
        outer.addWidget(card)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("🧩 Cloze 爆破（填空）")
        title.setStyleSheet(f"color:#111827;font-weight:800;font-size:{self.font_px+2}px;background:#ffffff;border:1px solid #d1d5db;border-radius:10px;padding:8px 12px;")
        layout.addWidget(title)

        # Timer + hint row
        row_top = QHBoxLayout()
        self.timer_label = QLabel("")
        self.timer_label.setStyleSheet(f"color:#dc2626;font-size:{self.font_px-2}px;font-weight:700")
        row_top.addWidget(self.timer_label)
        row_top.addStretch()
        layout.addLayout(row_top)

        self.timer_bar = QProgressBar()
        self.timer_bar.setRange(0, self.per_item_ms)
        self.timer_bar.setValue(self.per_item_ms)
        self.timer_bar.setTextVisible(False)
        self.timer_bar.setStyleSheet("QProgressBar{border:1px solid #cbd5e1;border-radius:6px;height:8px;background:#f1f5f9;} QProgressBar::chunk{background-color:#3b82f6;border-radius:6px;}")
        layout.addWidget(self.timer_bar)

        stats_card = QWidget()
        stats_card.setStyleSheet("background:#ffffff;border:1px solid #d1d5db;border-radius:10px;padding:6px 10px;")
        stats_row = QHBoxLayout(stats_card)
        stats_row.setContentsMargins(6, 2, 6, 2)
        stats_row.setSpacing(12)

        def _badge(text: str) -> QLabel:
            lbl = QLabel(text)
            lbl.setStyleSheet(f"color:#0f172a;font-size:{self.font_px-2}px;font-weight:600;")
            return lbl

        self.progress_badge = _badge("")
        self.correct_badge = _badge("")
        self.hint_badge = _badge("")
        stats_row.addWidget(self.progress_badge)
        stats_row.addWidget(self.correct_badge)
        stats_row.addWidget(self.hint_badge)
        stats_row.addStretch()
        layout.addWidget(stats_card)

        self.sentence_label = QLabel("")
        self.sentence_label.setWordWrap(True)
        self.sentence_label.setStyleSheet(f"color:#0b1a33;font-size:{self.font_px}px;background:#ffffff;border:1px solid #e5e7eb;border-radius:12px;padding:12px;")
        layout.addWidget(self.sentence_label)

        self.translation_label = QLabel("")
        self.translation_label.setWordWrap(True)
        self.translation_label.setStyleSheet(f"color:#1f2937;font-size:{self.font_px-2}px;background:#eef2ff;border:1px solid #c7d2fe;border-radius:10px;padding:10px;")
        self.translation_label.setVisible(False)
        layout.addWidget(self.translation_label)

        self.hint_label = QLabel("")
        self.hint_label.setStyleSheet(f"color:#64748b;font-size:{self.font_px-2}px")
        layout.addWidget(self.hint_label)

        row = QHBoxLayout()
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("输入缺失的英文单词/短语… 回车提交")
        self.input_edit.setStyleSheet(f"font-size:{self.font_px}px;padding:8px;border:1px solid #cbd5e1;border-radius:8px;")
        self.input_edit.returnPressed.connect(self._submit)
        row.addWidget(self.input_edit)

        self.hint_btn = QPushButton("提示 (H)")
        self.hint_btn.clicked.connect(self._hint)
        row.addWidget(self.hint_btn)

        self.next_btn = QPushButton("跳过 (S)")
        self.next_btn.clicked.connect(self._skip)
        row.addWidget(self.next_btn)
        layout.addLayout(row)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet(f"color:#475569;font-size:{self.font_px-2}px")
        layout.addWidget(self.status_label)

        self.recap_label = QLabel("上一题解析会显示在这里。")
        self.recap_label.setWordWrap(True)
        self.recap_label.setTextFormat(Qt.RichText)
        self.recap_label.setStyleSheet(f"color:#0f172a;font-size:{self.font_px-2}px;background:#f8fafc;border:1px dashed #cbd5e1;border-radius:10px;padding:10px;")
        layout.addWidget(self.recap_label)
        self._update_meta()

    def _pick_sentence(self, item: Dict):
        term = item.get('term') or ''
        contexts = item.get('contexts') or []
        sent = ''
        translation = ''
        for c in contexts:
            src = (c.get('source_text') or '').strip()
            tgt = (c.get('translated_text') or c.get('translation') or c.get('target_text') or '').strip()
            if not src:
                continue
            # pick the first sentence containing term
            parts = re.split(r'(?<=[.!?。！？])\s+', src)
            translations = re.split(r'(?<=[.!?。！？])\s+', tgt) if tgt else []
            for idx, p in enumerate(parts):
                if term and re.search(re.escape(term), p, flags=re.IGNORECASE):
                    sent = p
                    if translations and idx < len(translations):
                        translation = translations[idx]
                    elif tgt:
                        translation = tgt
                    break
            if sent:
                if not translation and tgt:
                    translation = tgt
                break
        if not sent:
            sent = (contexts[0].get('source_text') if contexts else '') or f"Use {term} in context."
        if not translation:
            translation = item.get('translation') or (contexts[0].get('translated_text') if contexts else '') or ''
        return sent, make_cloze(sent, term), translation

    def _load_round(self):
        if self.index >= len(self.items):
            self._finish_game()
            return
        self.attempts = 0
        it = self.items[self.index]
        self._hint_used = False
        self.current_sentence_raw, cloze, translation = self._pick_sentence(it)
        self.current_answer = (it.get('term') or '').strip()
        self.current_translation = translation.strip()
        self.sentence_label.setText(cloze)
        if self.current_translation:
            safe_translation = html.escape(self.current_translation)
            self.translation_label.setText(f"译文：{safe_translation}")
            self.translation_label.setVisible(True)
        else:
            self.translation_label.clear()
            self.translation_label.setVisible(False)
        hint = it.get('game_hint') or it.get('translation') or it.get('hint') or ''
        self.hint_label.setText(f"提示：{hint}" if hint else '')
        self.input_edit.setText("")
        self.input_edit.setEnabled(True)
        self.status_label.setText(f"第 {self.index+1}/{len(self.items)} 题 · 回车提交 / H 提示 / S 跳过")
        self.input_edit.setFocus()
        # start per-item timer
        self.deadline_ms = self.per_item_ms
        self._update_timer_label()
        self.timer_bar.setMaximum(self.per_item_ms)
        self.timer_bar.setValue(self.deadline_ms)
        if not self.results:
            self.recap_label.setText("上一题解析会显示在这里。")
        self._update_meta()
        self._round_active = True
        self.timer.start(200)

    def _submit(self):
        it = self.items[self.index]
        ans = (it.get('term') or '').strip()
        guess = (self.input_edit.text() or '').strip()
        self.attempts += 1
        if _is_close_match(guess, ans):
            # grade by attempts: 3 -> first try, 2 -> second, 1 -> >2 or used hint
            grade = 3 if self.attempts == 1 else (2 if self.attempts == 2 else 1)
            # time pressure: overtime caps at 1
            if self.deadline_ms <= 0:
                grade = min(grade, 1)
            verdict = "✅ 正确！"
            if grade == 1:
                verdict = "✅ 正确 · 建议再巩固"
            self._finalize_round(grade, verdict)
        else:
            self.status_label.setText("❌ 不对，再试一次或点提示")

    def _hint(self):
        if not self.items:
            return
        it = self.items[self.index]
        ans = (it.get('term') or '').strip()
        if not ans:
            return
        shown = len(self.input_edit.text())
        reveal = max(1, min(2, len(ans)//3))
        self.input_edit.setText(ans[:shown+reveal])
        # count as extra attempt for grading
        self.attempts = max(self.attempts, 2)
        if not self._hint_used:
            self._hint_used = True
            self.hint_count += 1
            self._update_meta()

    def _skip(self):
        it = self.items[self.index]
        # again
        self._finalize_round(0, "⚠️ 已跳过", delay=350)

    def _tick(self):
        self.deadline_ms -= 200
        self._update_timer_label()
        self.timer_bar.setValue(max(0, self.deadline_ms))
        if self.deadline_ms <= 0:
            # time up -> mark as hard (1) if attempted, else again (0)
            it = self.items[self.index]
            grade = 1 if self.attempts > 0 else 0
            verdict = "⏰ 超时（记1分）" if grade == 1 else "⏰ 超时（记0分）"
            self._finalize_round(grade, verdict, delay=500)

    def _update_timer_label(self):
        self.timer_label.setText(f"{max(0, self.deadline_ms//1000)}s")

    def _next(self):
        try:
            self.timer.stop()
        except Exception:
            pass
        self.index += 1
        self._load_round()

    def _finalize_round(self, grade: int, verdict: str, delay: int = 500):
        if not self._round_active:
            return
        self._round_active = False
        it = self.items[self.index]
        self.results.append({'id': it['id'], 'grade': grade})
        if grade >= 1:
            self.correct_count += 1
        else:
            self.skip_count += 1
        self.status_label.setText(verdict)
        self.input_edit.setEnabled(False)
        self._set_recap(verdict, self.current_sentence_raw, self.current_answer, self.current_translation)
        self._update_meta()
        try:
            self.timer.stop()
        except Exception:
            pass
        QTimer.singleShot(delay, self._next)

    def _set_recap(self, verdict: str, sentence: str, answer: str, translation: str = ""):
        if not sentence:
            self.recap_label.setText(verdict)
            return
        highlighted = self._format_solution(sentence, answer)
        translation_html = ""
        if translation:
            translation_html = f"<br/><span style='color:#1d4ed8'>{html.escape(translation)}</span>"
        self.recap_label.setText(f"{verdict}<br/>{highlighted}{translation_html}")

    def _format_solution(self, sentence: str, answer: str) -> str:
        safe_sentence = html.escape(sentence or '')
        if not answer:
            return safe_sentence
        safe_answer = html.escape(answer or '')
        try:
            pattern = re.compile(re.escape(safe_answer), flags=re.IGNORECASE)
            return pattern.sub(lambda m: f"<span style='color:#2563eb;font-weight:700'>{m.group(0)}</span>", safe_sentence, count=1)
        except Exception:
            return safe_sentence

    def _update_meta(self):
        total = max(1, self.total_rounds)
        current = min(self.index + 1, total)
        self.progress_badge.setText(f"进度 {current}/{total}")
        self.correct_badge.setText(f"完成 {self.correct_count} · 跳过 {self.skip_count}")
        self.hint_badge.setText(f"提示 {self.hint_count}")

    def _finish_game(self):
        try:
            self.timer.stop()
        except Exception:
            pass
        # brief summary
        try:
            mastered = sum(1 for r in self.results if r.get('grade', 0) >= 2)
            hard = sum(1 for r in self.results if r.get('grade', 0) == 1)
            again = sum(1 for r in self.results if r.get('grade', 0) == 0)
            total = len(self.items)
            summary = (
                f"Cloze 完成（≥2分）：{mastered}/{total}\n"
                f"困难卡（1分）：{hard} · 跳过/超时：{again}\n"
                f"提示使用：{self.hint_count} 次"
            )
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Information)
            box.setWindowTitle("本局总结")
            box.setTextInteractionFlags(Qt.TextSelectableByMouse)
            box.setTextFormat(Qt.PlainText)
            box.setText(summary)
            box.setStyleSheet(
                "QLabel{color:#0f172a;font-size:13px;} "
                "QMessageBox{background-color:#ffffff;border-radius:12px;}"
            )
            box.exec_()
        except Exception:
            pass
        if callable(self.on_finish):
            try:
                self.on_finish(self.results)
            except Exception:
                pass
        self.accept()

    # shortcuts
    def keyPressEvent(self, e):
        try:
            key = e.key()
            if key in (Qt.Key_H,):
                self._hint(); return
            if key in (Qt.Key_S,):
                self._skip(); return
            if key in (Qt.Key_Escape,):
                # early finish; grade remaining as 0
                try:
                    self.timer.stop()
                except Exception:
                    pass
                self._round_active = False
                for j in range(self.index, len(self.items)):
                    it = self.items[j]
                    self.results.append({'id': it['id'], 'grade': 0})
                    self.skip_count += 1
                self._update_meta()
                self._finish_game(); return
        except Exception:
            pass
        super().keyPressEvent(e)
