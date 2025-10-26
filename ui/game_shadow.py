from __future__ import annotations

import re
from typing import List, Dict, Callable, Optional
import string
import html

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QWidget, QLineEdit, QMessageBox, QProgressBar
)


def split_sentence(text: str) -> str:
    parts = re.split(r'(?<=[.!?])\s+', text or '')
    return parts[0] if parts else text


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
    if g == a:
        return True
    g = _strip_edges(g)
    a = _strip_edges(a)
    if g == a:
        return True
    dist = _levenshtein(g, a)
    if len(a) <= 5:
        return dist <= 1
    return dist <= max(2, len(a) // 6)


class TTS:
    def __init__(self):
        self.engine = None
        try:
            import pyttsx3  # type: ignore
            self.engine = pyttsx3.init()
            # Slightly slower and clearer
            try:
                rate = self.engine.getProperty('rate')
                self.engine.setProperty('rate', int(rate*0.9))
            except Exception:
                pass
            # Prefer an English voice if available
            try:
                voices = self.engine.getProperty('voices') or []
                def is_en(v):
                    name = (getattr(v, 'name', '') or '').lower()
                    langs = (getattr(v, 'languages', []) or [])
                    return 'en' in name or any('en' in str(x).lower() for x in langs)
                for v in voices:
                    if is_en(v):
                        self.engine.setProperty('voice', v.id)
                        break
            except Exception:
                pass
        except Exception:
            self.engine = None

    def set_rate_factor(self, factor: float):
        if self.engine is None:
            return
        try:
            base = self.engine.getProperty('rate')
            self.engine.setProperty('rate', int(max(80, min(300, base * factor))))
        except Exception:
            pass

    def speak(self, text: str):
        if not text:
            return
        if self.engine is None:
            # Best-effort fallback: do nothing
            return
        try:
            self.engine.stop()
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception:
            pass


class GameShadow(QDialog):
    """Shadowing-light: Listen and type the key word/phrase."""

    def __init__(self, items: List[Dict], on_finish: Optional[Callable[[List[Dict]], None]] = None,
                 rounds: int = 3, parent=None, font_px: int = 16, per_item_seconds: int = 15):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        try:
            self.setAttribute(Qt.WA_DeleteOnClose)
        except Exception:
            pass
        self.items = items[:max(1, rounds)]
        self.on_finish = on_finish
        self.font_px = max(12, min(int(font_px), 24))
        self.index = 0
        self.results: List[Dict] = []
        self.attempts = 0
        self.tts = TTS()
        self.rate_factor = 1.0
        self.per_item_seconds = max(8, min(int(per_item_seconds), 60))
        self.per_item_ms = self.per_item_seconds * 1000
        self.deadline_ms = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.total_rounds = len(self.items)
        self.correct_count = 0
        self.skip_count = 0
        self.hint_count = 0
        self.play_count = 0
        self.total_playbacks = 0
        self._hint_used = False
        self._round_active = False

        self._build_ui()
        self._load_round()

    def _build_ui(self):
        self.setMinimumSize(600, 220)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        self.title = QLabel("🎧 影子跟读（听写关键词）")
        self.title.setStyleSheet(f"color:#111827;font-weight:800;font-size:{self.font_px+2}px;background:#ffffff;border:1px solid #d1d5db;border-radius:10px;padding:8px 12px;")
        layout.addWidget(self.title)

        # Timer + prompt
        top = QHBoxLayout()
        self.timer_label = QLabel("")
        self.timer_label.setStyleSheet(f"color:#dc2626;font-size:{self.font_px-2}px;font-weight:700")
        top.addWidget(self.timer_label)
        self.prompt = QLabel("点击播放，输入关键词；H 提示，S 跳过")
        self.prompt.setStyleSheet(f"color:#334155;font-size:{self.font_px-2}px")
        top.addStretch()
        layout.addLayout(top)

        self.timer_bar = QProgressBar()
        self.timer_bar.setRange(0, self.per_item_ms)
        self.timer_bar.setValue(self.per_item_ms)
        self.timer_bar.setTextVisible(False)
        self.timer_bar.setStyleSheet("QProgressBar{border:1px solid #cbd5e1;border-radius:6px;height:8px;background:#f1f5f9;} QProgressBar::chunk{background-color:#f97316;border-radius:6px;}")
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
        self.score_badge = _badge("")
        self.rate_badge = _badge("")
        self.play_badge = _badge("")
        stats_row.addWidget(self.progress_badge)
        stats_row.addWidget(self.score_badge)
        stats_row.addWidget(self.rate_badge)
        stats_row.addWidget(self.play_badge)
        stats_row.addStretch()
        layout.addWidget(stats_card)
        layout.addWidget(self.prompt)

        row = QHBoxLayout()
        self.play_btn = QPushButton("▶ 播放")
        self.play_btn.clicked.connect(self._play)
        row.addWidget(self.play_btn)

        self.repeat_btn = QPushButton("↺ 重播")
        self.repeat_btn.clicked.connect(self._play)
        row.addWidget(self.repeat_btn)

        self.slower_btn = QPushButton("－ 速度")
        self.slower_btn.clicked.connect(lambda: self._adjust_rate(-0.1))
        row.addWidget(self.slower_btn)

        self.faster_btn = QPushButton("＋ 速度")
        self.faster_btn.clicked.connect(lambda: self._adjust_rate(+0.1))
        row.addWidget(self.faster_btn)
        layout.addLayout(row)

        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("输入你听到的关键词/短语… 回车提交")
        self.input_edit.setStyleSheet(f"font-size:{self.font_px}px;padding:8px;border:1px solid #cbd5e1;border-radius:8px;")
        self.input_edit.returnPressed.connect(self._submit)
        layout.addWidget(self.input_edit)

        self.hint_label = QLabel("")
        self.hint_label.setStyleSheet(f"color:#64748b;font-size:{self.font_px-2}px")
        layout.addWidget(self.hint_label)

        self.status = QLabel("")
        self.status.setStyleSheet(f"color:#475569;font-size:{self.font_px-2}px")
        layout.addWidget(self.status)

        self.recap_label = QLabel("上一题解析会显示在这里。")
        self.recap_label.setWordWrap(True)
        self.recap_label.setTextFormat(Qt.RichText)
        self.recap_label.setStyleSheet(f"color:#0f172a;font-size:{self.font_px-2}px;background:#f8fafc;border:1px dashed #cbd5e1;border-radius:10px;padding:10px;")
        layout.addWidget(self.recap_label)
        self._update_meta()

    def _pick_sentence(self, item: Dict) -> str:
        term = (item.get('term') or '').strip()
        contexts = item.get('contexts') or []
        for c in contexts:
            src = (c.get('source_text') or '').strip()
            if not src:
                continue
            parts = re.split(r'(?<=[.!?])\s+', src)
            for p in parts:
                if term and re.search(re.escape(term), p, flags=re.IGNORECASE):
                    return split_sentence(p)
        return split_sentence((contexts[0].get('source_text') if contexts else '') or f"Please remember {term}.")

    def _load_round(self):
        if self.index >= len(self.items):
            self._finish()
            return
        self.attempts = 0
        self.cur = self.items[self.index]
        self.sentence = self._pick_sentence(self.cur)
        self._hint_used = False
        self.play_count = 0
        self.status.setText(f"第 {self.index+1}/{len(self.items)} 题")
        self.input_edit.setText("")
        self.input_edit.setEnabled(True)
        hint = self.cur.get('game_hint') or self.cur.get('translation') or self.cur.get('hint') or ''
        self.hint_label.setText(f"提示：{hint}" if hint else '')
        self.deadline_ms = self.per_item_ms
        self._update_timer_label()
        self.timer_bar.setMaximum(self.per_item_ms)
        self.timer_bar.setValue(self.deadline_ms)
        if not self.results:
            self.recap_label.setText("上一题解析会显示在这里。")
        self._update_meta()
        self._round_active = True
        self.timer.start(200)

    def _play(self):
        try:
            self.tts.set_rate_factor(self.rate_factor)
        except Exception:
            pass
        self.tts.speak(self.sentence)
        self.play_count += 1
        self.total_playbacks += 1
        self.status.setText(f"🔊 已播放 {self.play_count} 次 · 按空格可重播")
        self._update_meta()

    def _submit(self):
        ans = (self.cur.get('term') or '').strip()
        guess = (self.input_edit.text() or '').strip()
        self.attempts += 1
        if _is_close_match(guess, ans):
            grade = 3 if self.attempts == 1 else (2 if self.attempts == 2 else 1)
            if self.deadline_ms <= 0:
                grade = min(grade, 1)
            verdict = "✅ 正确！" if grade >= 2 else "✅ 正确 · 建议再听"
            self._finalize_round(grade, verdict)
        else:
            self.status.setText("❌ 不对，再试或重播")

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
        self.results.append({'id': self.cur['id'], 'grade': grade})
        if grade >= 1:
            self.correct_count += 1
        else:
            self.skip_count += 1
        self.status.setText(verdict)
        self.input_edit.setEnabled(False)
        self._set_recap(verdict, self.sentence, (self.cur.get('term') or '').strip())
        self._update_meta()
        try:
            self.timer.stop()
        except Exception:
            pass
        QTimer.singleShot(delay, self._next)

    def _set_recap(self, verdict: str, sentence: str, answer: str):
        if not sentence:
            self.recap_label.setText(verdict)
            return
        highlighted = self._format_solution(sentence, answer)
        self.recap_label.setText(f"{verdict}<br/>{highlighted}")

    def _format_solution(self, sentence: str, answer: str) -> str:
        safe_sentence = html.escape(sentence or '')
        if not answer:
            return safe_sentence
        safe_answer = html.escape(answer or '')
        try:
            pattern = re.compile(re.escape(safe_answer), flags=re.IGNORECASE)
            return pattern.sub(lambda m: f"<span style='color:#ea580c;font-weight:700'>{m.group(0)}</span>", safe_sentence, count=1)
        except Exception:
            return safe_sentence

    def _update_meta(self):
        total = max(1, self.total_rounds)
        current = min(self.index + 1, total)
        self.progress_badge.setText(f"进度 {current}/{total}")
        self.score_badge.setText(f"完成 {self.correct_count} · 跳过 {self.skip_count}")
        self.rate_badge.setText(f"语速 {self.rate_factor:.1f}x")
        self.play_badge.setText(f"播放 本题 {self.play_count} 次")

    def _finish(self):
        try:
            self.timer.stop()
        except Exception:
            pass
        # summary
        try:
            mastered = sum(1 for r in self.results if r.get('grade', 0) >= 2)
            hard = sum(1 for r in self.results if r.get('grade', 0) == 1)
            again = sum(1 for r in self.results if r.get('grade', 0) == 0)
            total = len(self.items)
            summary = (
                f"听写通过（≥2分）：{mastered}/{total}\n"
                f"困难卡：{hard} · 跳过/超时：{again}\n"
                f"提示：{self.hint_count} 次 · 累计播放：{self.total_playbacks} 次"
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

    def _adjust_rate(self, delta: float):
        self.rate_factor = max(0.6, min(1.4, self.rate_factor + delta))
        self.status.setText(f"语速：{self.rate_factor:.1f}x（Space 重播）")
        self._update_meta()

    def _tick(self):
        self.deadline_ms -= 200
        self._update_timer_label()
        self.timer_bar.setValue(max(0, self.deadline_ms))
        if self.deadline_ms <= 0:
            # time up
            grade = 1 if self.attempts > 0 else 0
            verdict = "⏰ 超时（记1分）" if grade == 1 else "⏰ 超时（记0分）"
            self._finalize_round(grade, verdict, delay=500)

    def _update_timer_label(self):
        self.timer_label.setText(f"{max(0, self.deadline_ms//1000)}s")

    # shortcuts
    def keyPressEvent(self, e):
        try:
            key = e.key()
            if key in (Qt.Key_H,):
                # reveal first few letters as cue
                ans = (self.cur.get('term') or '').strip()
                shown = len(self.input_edit.text())
                self.input_edit.setText(ans[:max(1, min(2, shown + max(1, len(ans)//3)))])
                self.attempts = max(self.attempts, 2)
                if not self._hint_used:
                    self._hint_used = True
                    self.hint_count += 1
                    self._update_meta()
                return
            if key in (Qt.Key_S,):
                # skip
                self._finalize_round(0, "⚠️ 已跳过", delay=350); return
            if key in (Qt.Key_Space,):
                self._play(); return
            if key in (Qt.Key_Escape,):
                # early finish
                try:
                    self.timer.stop()
                except Exception:
                    pass
                self._round_active = False
                for j in range(self.index, len(self.items)):
                    self.results.append({'id': self.items[j]['id'], 'grade': 0})
                    self.skip_count += 1
                self._update_meta()
                self._finish(); return
        except Exception:
            pass
        super().keyPressEvent(e)
