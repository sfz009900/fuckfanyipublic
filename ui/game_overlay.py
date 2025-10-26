import random
import time
import re
import html
from typing import List, Dict, Callable, Optional, Tuple
import threading

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QWidget, QGridLayout, QMessageBox, QProgressBar
)
from PyQt5.QtGui import QFont


class GameOverlay(QDialog):
    """Tiny topmost 15–45s Match-5 game: term ↔ Chinese hint."""

    def __init__(self, items: List[Dict], on_finish: Optional[Callable[[List[Dict]], None]] = None,
                 round_seconds: int = 25, parent=None, font_px: int = 16, high_contrast: bool = True,
                 capture_source_full: str = '', capture_translation_full: str = '',
                 ai_translate_fn: Optional[Callable[[str], Optional[str]]] = None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        # ensure deletion so caller can reopen next rounds
        try:
            self.setAttribute(Qt.WA_DeleteOnClose)
        except Exception:
            pass
        self.items = items[:5]
        self.on_finish = on_finish
        self.round_seconds = max(10, min(round_seconds, 60))
        self.font_px = max(12, min(int(font_px), 24))
        self.high_contrast = bool(high_contrast)
        self.selected_left = None
        self.selected_right = None
        self.mistakes: Dict[str, int] = {i['id']: 0 for i in self.items if 'id' in i}
        self.matches_left = len(self.items)
        self.total_pairs = len(self.items)
        self.correct_pairs = 0
        self.total_attempts = 0
        self.current_streak = 0
        self.best_streak = 0
        self.mistake_total = 0
        self._round_total_ms = self.round_seconds * 1000
        # Full capture texts from the exact screenshot session (preferred)
        self.capture_source_full = capture_source_full or ''
        self.capture_translation_full = capture_translation_full or ''
        # Optional AI translate function (e.g., OpenAI/Ollama via Translator)
        self.ai_translate_fn = ai_translate_fn
        self._ai_thread: Optional[threading.Thread] = None

        self._build_ui()
        self._start_timer()

    def _build_ui(self):
        self.setMinimumSize(560, 380)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel("🎮 轻松配对：术语 ↔ 提示")
        if self.high_contrast:
            title.setStyleSheet(f"color:#ffffff;font-weight:800;font-size:{self.font_px+2}px;background:#111827;border-radius:10px;padding:8px 12px;")
        else:
            title.setStyleSheet(f"color:#0b1a33;font-weight:700;font-size:{self.font_px+2}px;background:#ffffff;border-radius:10px;padding:8px 12px;")
        layout.addWidget(title)

        # Timer + status
        bar = QHBoxLayout()
        self.timer_label = QLabel(f"{self.round_seconds}s")
        self.timer_label.setStyleSheet(f"color:#dc2626;font-size:{self.font_px}px;font-weight:800")
        self.status_label = QLabel("配对全部即可通关！(Esc 结束)")
        self.status_label.setStyleSheet(f"color:#334155;font-size:{self.font_px-2}px")
        bar.addWidget(self.timer_label)
        bar.addStretch()
        bar.addWidget(self.status_label)
        layout.addLayout(bar)

        self.timer_bar = QProgressBar()
        self.timer_bar.setRange(0, self._round_total_ms)
        self.timer_bar.setValue(self._round_total_ms)
        self.timer_bar.setTextVisible(False)
        self.timer_bar.setStyleSheet("QProgressBar{border:1px solid #cbd5e1;border-radius:6px;height:10px;background:#f1f5f9;} QProgressBar::chunk{background-color:#22c55e;border-radius:6px;}")
        layout.addWidget(self.timer_bar)

        stats_card = QWidget()
        stats_card.setStyleSheet("background:#ffffff;border:1px solid #d1d5db;border-radius:10px;padding:10px;")
        stats_row = QHBoxLayout(stats_card)
        stats_row.setContentsMargins(8, 4, 8, 4)
        stats_row.setSpacing(12)

        def _badge(text: str) -> QLabel:
            lbl = QLabel(text)
            lbl.setStyleSheet(f"color:#0f172a;font-size:{self.font_px-2}px;font-weight:600;")
            return lbl

        self.progress_badge = _badge("")
        self.accuracy_badge = _badge("")
        self.streak_badge = _badge("")
        self.mistake_badge = _badge("")
        stats_row.addWidget(self.progress_badge)
        stats_row.addWidget(self.accuracy_badge)
        stats_row.addWidget(self.streak_badge)
        stats_row.addWidget(self.mistake_badge)
        stats_row.addStretch()
        layout.addWidget(stats_card)

        # Board
        board = QWidget()
        if self.high_contrast:
            board.setStyleSheet("background:#ffffff;border:1px solid #94a3b8;border-radius:12px;")
        else:
            board.setStyleSheet("background:#ffffff;border:1px solid #d8e0ea;border-radius:12px;")
        grid = QGridLayout(board)
        grid.setContentsMargins(12, 12, 12, 12)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)

        left_terms = [(i['id'], i.get('term','')) for i in self.items]
        right_hints = [(i['id'], i.get('game_hint') or i.get('translation') or i.get('hint') or '') for i in self.items]
        random.shuffle(left_terms)
        random.shuffle(right_hints)

        self.left_buttons: Dict[str, QPushButton] = {}
        self.right_buttons: Dict[str, QPushButton] = {}

        btn_font = QFont("Microsoft YaHei UI", max(10, int(self.font_px*0.9)))

        def default_left_style() -> str:
            if self.high_contrast:
                return (
                    f"QPushButton{{background:#eef2ff;color:#0b1a33;border:1px solid #93c5fd;"
                    f"border-radius:8px;padding:10px;text-align:left;font-size:{self.font_px}px;}} "
                    f"QPushButton:checked{{background:#dbeafe;border-color:#60a5fa}}"
                )
            else:
                return (
                    f"QPushButton{{background:#f1f5f9;color:#0b1a33;border:1px solid #cbd5e1;"
                    f"border-radius:8px;padding:10px;text-align:left;font-size:{self.font_px}px;}} "
                    f"QPushButton:checked{{background:#dbeafe;border-color:#93c5fd}}"
                )

        def default_right_style() -> str:
            if self.high_contrast:
                return (
                    f"QPushButton{{background:#ffffff;color:#0b1a33;border:1px solid #94a3b8;"
                    f"border-radius:8px;padding:10px;text-align:left;font-size:{self.font_px}px;}} "
                    f"QPushButton:checked{{background:#fef9c3;border-color:#f59e0b}}"
                )
            else:
                return (
                    f"QPushButton{{background:#fafafa;color:#0b1a33;border:1px solid #e5e7eb;"
                    f"border-radius:8px;padding:10px;text-align:left;font-size:{self.font_px}px;}} "
                    f"QPushButton:checked{{background:#fef9c3;border-color:#fde68a}}"
                )

        self._left_default_style = default_left_style()
        self._right_default_style = default_right_style()

        def apply_result_style(btn: QPushButton, success: bool):
            if success:
                if self.high_contrast:
                    btn.setStyleSheet(
                        f"QPushButton{{background:#dcfce7;color:#065f46;border:1px solid #86efac;"
                        f"border-radius:8px;padding:10px;text-align:left;font-size:{self.font_px}px;}}"
                    )
                else:
                    btn.setStyleSheet(
                        f"QPushButton{{background:#dcfce7;color:#065f46;border:1px solid #86efac;"
                        f"border-radius:8px;padding:10px;text-align:left;font-size:{self.font_px}px;}}"
                    )
            else:
                if self.high_contrast:
                    btn.setStyleSheet(
                        f"QPushButton{{background:#fee2e2;color:#7f1d1d;border:1px solid #fecaca;"
                        f"border-radius:8px;padding:10px;text-align:left;font-size:{self.font_px}px;}}"
                    )
                else:
                    btn.setStyleSheet(
                        f"QPushButton{{background:#fee2e2;color:#7f1d1d;border:1px solid #fecaca;"
                        f"border-radius:8px;padding:10px;text-align:left;font-size:{self.font_px}px;}}"
                    )
        self._apply_result_style = apply_result_style

        for row, (iid, term) in enumerate(left_terms):
            b = QPushButton(term)
            b.setCheckable(True)
            b.clicked.connect(lambda _=False, bid=iid: self._pick_left(bid))
            b.setFont(btn_font)
            b.setMinimumHeight(42)
            b.setToolTip(term)
            b.setStyleSheet(self._left_default_style)
            self.left_buttons[iid] = b
            grid.addWidget(b, row, 0)

        for row, (iid, hint) in enumerate(right_hints):
            b = QPushButton(hint or "（无提示）")
            b.setCheckable(True)
            b.clicked.connect(lambda _=False, bid=iid: self._pick_right(bid))
            b.setFont(btn_font)
            b.setMinimumHeight(42)
            b.setToolTip(hint or "")
            b.setStyleSheet(self._right_default_style)
            self.right_buttons[iid] = b
            grid.addWidget(b, row, 1)

        layout.addWidget(board)

        # Full source & translation (like GameCloze)
        self.full_source_label = QLabel("")
        self.full_source_label.setWordWrap(True)
        self.full_source_label.setVisible(True)
        self.full_source_label.setTextFormat(Qt.RichText)
        self.full_source_label.setStyleSheet(
            f"color:#0b1a33;font-size:{self.font_px}px;background:#ffffff;"
            f"border:1px solid #e5e7eb;border-radius:12px;padding:10px;"
        )
        layout.addWidget(self.full_source_label)

        self.full_translation_label = QLabel("")
        self.full_translation_label.setWordWrap(True)
        self.full_translation_label.setVisible(True)
        self.full_translation_label.setTextFormat(Qt.RichText)
        self.full_translation_label.setStyleSheet(
            f"color:#1f2937;font-size:{self.font_px-2}px;background:#eef2ff;"
            f"border:1px solid #c7d2fe;border-radius:10px;padding:10px;"
        )
        layout.addWidget(self.full_translation_label)

        # Footer
        footer = QHBoxLayout()
        quit_btn = QPushButton("跳过")
        quit_btn.clicked.connect(self._finish)
        quit_btn.setStyleSheet(f"QPushButton{{background:#e2e8f0;color:#0b1a33;border:1px solid #cbd5e1;border-radius:8px;padding:8px 12px;font-weight:600;font-size:{max(12,self.font_px-2)}px;}} QPushButton:hover{{background:#cbd5e1}}")
        footer.addStretch()
        footer.addWidget(quit_btn)
        layout.addLayout(footer)
        self._update_stats()
        # Initialize with capture-level full texts if available
        if self.capture_source_full:
            # Always prefer the screenshot OCR text as 原文
            self.full_source_label.setText(f"原文：{html.escape(self.capture_source_full)}")
            self.full_source_label.setVisible(True)
            # For 译文: prefer captured translation immediately; AI only if missing
            if self.capture_translation_full:
                self.full_translation_label.setText(f"译文：{html.escape(self.capture_translation_full)}")
                self.full_translation_label.setVisible(True)
            elif callable(self.ai_translate_fn):
                self.full_translation_label.setText("译文：正在用AI翻译…")
                self.full_translation_label.setVisible(True)
                self._start_ai_translation_for_capture()
        else:
            # fallback to first item's context-derived texts
            try:
                if self.items:
                    self._update_full_text_by_id(self.items[0].get('id'))
            except Exception:
                pass

    def _extract_full_text(self, item: Dict) -> Tuple[str, str]:
        """Return full source and translation similar to GameCloze logic.

        - Prefer the context whose source contains the term (case-insensitive).
        - Fallback to the first context or item-level fields.
        """
        term = (item.get('term') or '').strip()
        contexts = item.get('contexts') or []
        src_full = ''
        tgt_full = ''
        def _tgt(c: Dict) -> str:
            return (c.get('translated_text') or c.get('translation') or c.get('target_text') or '').strip()

        # Try best-match context
        for c in contexts:
            src = (c.get('source_text') or '').strip()
            if not src:
                continue
            try:
                if term and re.search(re.escape(term), src, flags=re.IGNORECASE):
                    src_full = src
                    tgt_full = _tgt(c)
                    break
            except Exception:
                # fallback: accept this context
                src_full = src
                tgt_full = _tgt(c)
                break

        # Fallback to first context
        if not src_full and contexts:
            src_full = (contexts[0].get('source_text') or '').strip()
            tgt_full = _tgt(contexts[0])

        # Item-level fallbacks
        if not src_full:
            src_full = (item.get('source_text') or '').strip()
        if not tgt_full:
            tgt_full = (item.get('translation') or '').strip()

        return src_full, tgt_full

    def _update_full_text_by_id(self, item_id: Optional[str]):
        if not item_id:
            return
        # Prefer exact screenshot full texts if provided
        if self.capture_source_full:
            self.full_source_label.setText(f"原文：{html.escape(self.capture_source_full)}")
            self.full_source_label.setVisible(True)
            # 译文优先使用已有结果；仅在缺失时再异步AI
            if self.capture_translation_full:
                self.full_translation_label.setText(f"译文：{html.escape(self.capture_translation_full)}")
                self.full_translation_label.setVisible(True)
            elif callable(self.ai_translate_fn):
                self.full_translation_label.setText("译文：正在用AI翻译…")
                self.full_translation_label.setVisible(True)
                self._start_ai_translation_for_capture()
            else:
                self.full_translation_label.clear()
                self.full_translation_label.setVisible(False)
            return

        # Fallback: derive from selected item's contexts
        try:
            item = next((x for x in self.items if x.get('id') == item_id), None)
        except Exception:
            item = None
        if not item:
            return
        full_src, full_tgt = self._extract_full_text(item)
        if full_src:
            self.full_source_label.setText(f"原文：{html.escape(full_src)}")
            self.full_source_label.setVisible(True)
        else:
            self.full_source_label.clear()
            self.full_source_label.setVisible(False)
        if full_tgt:
            self.full_translation_label.setText(f"译文：{html.escape(full_tgt)}")
            self.full_translation_label.setVisible(True)
        else:
            self.full_translation_label.clear()
            self.full_translation_label.setVisible(False)

    def _start_timer(self):
        self.deadline = time.time() + self.round_seconds
        self.start_time = time.time()
        self.t = QTimer(self)
        self.t.timeout.connect(self._tick)
        self.t.start(200)

    def _tick(self):
        left = max(0, int(self.deadline - time.time()))
        self.timer_label.setText(f"{left}s")
        remaining_ms = max(0, int((self.deadline - time.time()) * 1000))
        self.timer_bar.setValue(remaining_ms)
        if left <= 0:
            self._finish()

    def _pick_left(self, item_id: str):
        # toggle others
        for k, b in self.left_buttons.items():
            b.setChecked(k == item_id)
        self.selected_left = item_id
        # preview full text for the selected item
        self._update_full_text_by_id(item_id)
        self._try_match()

    def _pick_right(self, item_id: str):
        for k, b in self.right_buttons.items():
            b.setChecked(k == item_id)
        self.selected_right = item_id
        # preview full text for the selected item (right side ids match items)
        self._update_full_text_by_id(item_id)
        self._try_match()

    def _try_match(self):
        if not self.selected_left or not self.selected_right:
            return
        left = self.selected_left
        right = self.selected_right
        # reset for next pick
        self.selected_left = None
        self.selected_right = None

        if left == right:
            self._record_attempt(success=True)
            # success
            lb = self.left_buttons[left]
            rb = self.right_buttons[right]
            # clear checks to remove yellow selection state
            try:
                lb.setChecked(False)
                rb.setChecked(False)
            except Exception:
                pass
            lb.setEnabled(False)
            rb.setEnabled(False)
            self._apply_result_style(lb, True)
            self._apply_result_style(rb, True)
            # Show full source/translation for this matched item only when no capture-level text
            if not self.capture_source_full:
                try:
                    item = next((x for x in self.items if x.get('id') == left), None)
                except Exception:
                    item = None
                if item:
                    full_src, full_tgt = self._extract_full_text(item)
                    if full_src:
                        safe_src = html.escape(full_src)
                        self.full_source_label.setText(f"原文：{safe_src}")
                        self.full_source_label.setVisible(True)
                    if full_tgt:
                        safe_tgt = html.escape(full_tgt)
                        self.full_translation_label.setText(f"译文：{safe_tgt}")
                        self.full_translation_label.setVisible(True)
            self.matches_left -= 1
            self.status_label.setText(f"✅ 正确！剩余 {self.matches_left} 组")
            if self.matches_left <= 0:
                self._finish()
        else:
            self._record_attempt(success=False)
            # mistake
            if left in self.mistakes:
                self.mistakes[left] += 1
            else:
                # register id if was disabled earlier
                self.mistakes[left] = 1
            self.status_label.setText("❌ 不对～再试一次！")
            # brief flash
            try:
                self._apply_result_style(self.left_buttons[left], False)
                self._apply_result_style(self.right_buttons[right], False)
                QTimer.singleShot(250, lambda: self._reset_styles(left, right))
            except Exception:
                pass

    def _reset_styles(self, left_id: str, right_id: str):
        if left_id in self.left_buttons:
            self.left_buttons[left_id].setStyleSheet(self._left_default_style)
            try:
                self.left_buttons[left_id].setChecked(False)
            except Exception:
                pass
        if right_id in self.right_buttons:
            self.right_buttons[right_id].setStyleSheet(self._right_default_style)
            try:
                self.right_buttons[right_id].setChecked(False)
            except Exception:
                pass

    def _record_attempt(self, success: bool):
        self.total_attempts += 1
        if success:
            self.correct_pairs += 1
            self.current_streak += 1
            self.best_streak = max(self.best_streak, self.current_streak)
        else:
            self.current_streak = 0
            self.mistake_total += 1
        self._update_stats()

    def _update_stats(self):
        if self.total_pairs <= 0:
            return
        progress = f"进度 {self.correct_pairs}/{self.total_pairs}"
        accuracy = 100 if self.total_attempts == 0 else int(round(self.correct_pairs / self.total_attempts * 100))
        streak = f"连击 {self.current_streak} | 最高 {self.best_streak}"
        mistakes = f"失误 {self.mistake_total}"
        self.progress_badge.setText(progress)
        self.accuracy_badge.setText(f"准确率 {accuracy}%")
        self.streak_badge.setText(streak)
        self.mistake_badge.setText(mistakes)

    def _finish(self):
        try:
            self.t.stop()
        except Exception:
            pass
        # Compute grades per item: 3 easy if no mistake, 2 good if 1 mistake, 1 hard if >=2, 0 again if not matched
        results = []
        solved = {iid for iid, b in self.left_buttons.items() if not b.isEnabled()}
        for it in self.items:
            iid = it['id']
            mistakes = int(self.mistakes.get(iid, 0))
            if iid in solved:
                if mistakes == 0:
                    grade = 3
                elif mistakes == 1:
                    grade = 2
                else:
                    grade = 1
            else:
                grade = 0
            results.append({'id': iid, 'grade': grade})
        # brief summary
        try:
            correct = self.correct_pairs
            total = self.total_pairs or len(self.items)
            elapsed = time.time() - getattr(self, 'start_time', time.time())
            acc = 100 if self.total_attempts == 0 else round(correct / max(1, self.total_attempts) * 100)
            summary = (
                f"配对完成：{correct}/{total}\n"
                f"准确率：{acc}%（{correct}/{max(1,self.total_attempts)}）\n"
                f"最佳连击：{self.best_streak}\n"
                f"用时：{elapsed:.1f}s"
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
                self.on_finish(results)
            except Exception:
                pass
        self.accept()

    # Pause timer if window loses focus (avoid penalizing user)
    def focusOutEvent(self, e):
        try:
            self._paused = True
            self.t.stop()
        except Exception:
            pass
        super().focusOutEvent(e)

    def focusInEvent(self, e):
        try:
            if getattr(self, '_paused', False):
                self._paused = False
                self.t.start(200)
        except Exception:
            pass
        super().focusInEvent(e)

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Escape,):
            self._finish(); return
        super().keyPressEvent(e)

    # ————————— AI translation helpers —————————
    def _start_ai_translation_for_capture(self):
        """Kick off background AI translation for the capture-level 原文 and update UI when done."""
        if not callable(self.ai_translate_fn) or not self.capture_source_full:
            return
        # avoid duplicate threads
        if self._ai_thread and self._ai_thread.is_alive():
            return

        def _job():
            try:
                result = self.ai_translate_fn(self.capture_source_full) or ''
            except Exception:
                result = ''

            def _apply():
                if result:
                    self.full_translation_label.setText(f"译文：{html.escape(result)}")
                    self.full_translation_label.setVisible(True)
                elif self.capture_translation_full:
                    # Fallback to captured translation if AI fails
                    self.full_translation_label.setText(f"译文：{html.escape(self.capture_translation_full)}")
                    self.full_translation_label.setVisible(True)
                else:
                    self.full_translation_label.setText("译文：<无>")
                    self.full_translation_label.setVisible(True)

            try:
                # marshal back to UI thread
                QTimer.singleShot(0, _apply)
            except Exception:
                _apply()

        self._ai_thread = threading.Thread(target=_job, daemon=True)
        self._ai_thread.start()
