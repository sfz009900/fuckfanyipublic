from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QTextCursor
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPlainTextEdit,
    QTextEdit, QPushButton, QMessageBox, QWidget, QSizePolicy, QSpacerItem
)
import requests


class _OllamaWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, original_text: str, model: str = "gpt-oss:120b-cloud", host: str = "http://127.0.0.1:11434"):
        super().__init__()
        self.original_text = original_text
        self.model = model
        self.host = host.rstrip("/")

    def run(self):
        try:
            # Prompt template with placeholder strictly as required
            prompt_template = (
                "你是一位顶级的AI英文学习教练，你的任务是帮助我用最快、最省力的方式“吃透”一段英文。\n"
                "你的回复必须严格遵循以下【三步学习法】框架，风格必须“极其简洁、通俗易懂、直击要害”，杜绝任何客套和废话。\n\n"
                "**【第一步：翻译】**\n"
                "提供原文流畅、地道的中文翻译。\n\n"
                "**【第二步：拆解,以最通俗易懂的方式让我记住关键词汇,显示为表格形式】**\n"
                "- **核心词汇/短语**：提炼关键点，格式为：`词汇 + 词汇或短语的中文类型名称比如动词 + 通俗解释`。\n"
                "- **关键句型**：如果原文有值得学习的句型，用一句话点明它的用法。\n\n"
                "**【第三步：词汇或短语巩固(显示为表格形式格式为:举例的英文句子-词汇或者短语-举例语句的完整翻译)】**\n"
                "用每一个核心关键词汇和关键句型单独举例实际用法和对应的翻译来让我加深记忆，让我能把核心信息刻在脑子里。\n\n"
                "现在，请处理以下英文原文：\n"
                '"{这里替换成原文}"'
            )
            prompt = prompt_template.replace("这里替换成原文", self.original_text)

            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
            }

            resp = requests.post(f"{self.host}/api/generate", json=payload, timeout=120)
            if resp.status_code != 200:
                self.error.emit(f"请求失败: HTTP {resp.status_code} | {resp.text[:500]}")
                return
            data = resp.json()
            content = data.get("response", "").strip()
            if not content:
                self.error.emit("模型未返回内容")
                return
            self.finished.emit(content)
        except Exception as e:
            self.error.emit(str(e))


class AIStudyDialog(QDialog):
    """AI学习窗口: 输入英文原文，点击学习，调用本地Ollama并显示结果。"""

    def __init__(self, parent=None, initial_text: str = None, auto_start: bool = False):
        super().__init__(parent)
        self.setWindowTitle("AI学习")
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setModal(True)
        self._worker = None

        self._build_ui()
        self._apply_styles()
        
        # 当在“学习结果”中选择文本时，尝试在“英文原文”中高亮匹配
        try:
            self.output_edit.selectionChanged.connect(self._on_output_selection_changed)
        except Exception:
            pass

        # Optional prefill and auto start
        if initial_text:
            try:
                self.input_edit.setPlainText(initial_text)
                if auto_start:
                    # 延迟到事件循环以确保控件已渲染
                    from PyQt5.QtCore import QTimer
                    QTimer.singleShot(0, self._on_learn_clicked)
            except Exception:
                pass

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        # Title
        title = QLabel("AI学习")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        # Input area
        input_label = QLabel("英文原文")
        input_label.setObjectName("sectionLabel")
        layout.addWidget(input_label)

        self.input_edit = QPlainTextEdit()
        self.input_edit.setPlaceholderText("在此粘贴或输入英文原文…")
        self.input_edit.setMinimumHeight(120)
        layout.addWidget(self.input_edit)

        # Action bar
        action_bar = QHBoxLayout()
        self.learn_btn = QPushButton("学习")
        self.learn_btn.clicked.connect(self._on_learn_clicked)
        self.learn_btn.setDefault(True)

        self.clear_btn = QPushButton("清空")
        self.clear_btn.clicked.connect(lambda: self.input_edit.clear())

        action_bar.addWidget(self.learn_btn)
        action_bar.addWidget(self.clear_btn)
        action_bar.addItem(QSpacerItem(20, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        layout.addLayout(action_bar)

        # Output area
        output_label = QLabel("学习结果")
        output_label.setObjectName("sectionLabel")
        layout.addWidget(output_label)

        output_card = QWidget()
        output_card.setObjectName("outputCard")
        output_layout = QVBoxLayout(output_card)
        output_layout.setContentsMargins(14, 14, 14, 14)
        output_layout.setSpacing(8)

        self.status_label = QLabel("结果将显示在这里。")
        self.status_label.setObjectName("statusLabel")
        output_layout.addWidget(self.status_label)

        self.output_edit = QTextEdit()
        self.output_edit.setReadOnly(True)
        self.output_edit.setObjectName("outputText")
        self.output_edit.setPlaceholderText("等待生成…")
        self.output_edit.setMinimumHeight(240)
        output_layout.addWidget(self.output_edit)

        layout.addWidget(output_card)

        # Footer
        footer = QHBoxLayout()
        self.copy_btn = QPushButton("复制结果")
        self.copy_btn.clicked.connect(self._copy_result)
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.close)
        footer.addWidget(self.copy_btn)
        footer.addItem(QSpacerItem(20, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        footer.addWidget(self.close_btn)
        layout.addLayout(footer)

        self.setMinimumSize(780, 560)

    # ———————————————————————— 选择联动高亮 ————————————————————————
    def _on_output_selection_changed(self):
        """当在“学习结果”中选中文本时，在“英文原文”中高亮所有匹配。"""
        try:
            cursor = self.output_edit.textCursor()
            selected = cursor.selectedText() or ""
            # QTextEdit 将换行表示为 \u2029，需要与原文的 \n 对齐
            selected = selected.replace("\u2029", "\n")
            # 去除两侧空白，避免选中纯空格时大面积高亮
            if selected.strip():
                self._highlight_in_input(selected)
            else:
                self._clear_input_highlight()
        except Exception:
            self._clear_input_highlight()

    def _clear_input_highlight(self):
        try:
            self.input_edit.setExtraSelections([])
        except Exception:
            pass

    def _highlight_in_input(self, term: str):
        """在 input_edit 中高亮 term 的所有出现（忽略大小写、精确匹配）。"""
        try:
            text = self.input_edit.toPlainText() or ""
            if not text:
                self._clear_input_highlight()
                return

            selections = []
            # 使用 lower() 保持长度一致，实现不区分大小写匹配
            lower_text = text.lower()
            lower_term = term.lower()
            start = 0
            term_len = len(term)
            # 避免极端情况下空串死循环
            if term_len == 0:
                self._clear_input_highlight()
                return

            while True:
                idx = lower_text.find(lower_term, start)
                if idx == -1:
                    break
                cur = self.input_edit.textCursor()
                cur.setPosition(idx, QTextCursor.MoveAnchor)
                cur.setPosition(idx + term_len, QTextCursor.KeepAnchor)
                sel = QTextEdit.ExtraSelection()
                # 柔和的浅黄色高亮
                sel.format.setBackground(QColor(255, 239, 170))
                sel.cursor = cur
                selections.append(sel)
                start = idx + term_len

            self.input_edit.setExtraSelections(selections)
        except Exception:
            # 出错时清除高亮以免残留
            self._clear_input_highlight()

    def _apply_styles(self):
        # Light, low-contrast, eye-comfort palette
        self.setStyleSheet(
            """
            QDialog { background: #fafbfe; }
            #titleLabel { color: #0b1a33; font-size: 20px; font-weight: 700; }
            #sectionLabel { color: #566379; font-size: 13px; margin-top: 2px; }
            QPlainTextEdit { color: #0b1a33; background: #ffffff; border: 1px solid #d8e0ea; border-radius: 8px; padding: 10px; font-size: 13px; }
            QPushButton { background: #2b67f6; color: #ffffff; border: none; border-radius: 6px; padding: 8px 14px; font-weight: 600; }
            QPushButton:hover { background: #356df5; }
            QPushButton:disabled { background: #e2e8f0; color: #98a2b3; }
            #outputCard { background: #ffffff; border: 1px solid #d8e0ea; border-radius: 12px; }
            #statusLabel { color: #6b7a8d; font-size: 12px; }
            #outputText { color: #0b1a33; background: transparent; border: none; font-size: 16px; }
            """
        )

        # Comfortable fonts for Chinese reading
        try:
            font = QFont("Microsoft YaHei UI", 10)
            self.input_edit.setFont(font)
            out_font = QFont("Microsoft YaHei UI", 11)
            self.output_edit.setFont(out_font)
        except Exception:
            pass

    def _on_learn_clicked(self):
        text = (self.input_edit.toPlainText() or "").strip()
        if not text:
            QMessageBox.information(self, "提示", "请先输入英文原文。")
            return

        # Reset UI state
        self.status_label.setText("正在学习中，请稍候…")
        self.output_edit.clear()
        self._set_busy(True)

        # Start worker
        self._worker = _OllamaWorker(text)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_finished(self, content: str):
        self._set_busy(False)
        self.status_label.setText("生成完成 (Markdown)")
        # Render markdown if supported; fallback to plain text
        if hasattr(self.output_edit, 'setMarkdown'):
            self.output_edit.setMarkdown(content)
        else:
            self.output_edit.setPlainText(content)

    def _on_error(self, message: str):
        self._set_busy(False)
        self.status_label.setText("出错了")
        QMessageBox.warning(self, "AI学习", message)

    def _set_busy(self, busy: bool):
        self.learn_btn.setDisabled(busy)
        self.clear_btn.setDisabled(busy)
        self.copy_btn.setDisabled(busy)
        self.close_btn.setDisabled(False)

    def _copy_result(self):
        text = self.output_edit.toPlainText()
        if text:
            self.clipboard().setText(text)
            self.status_label.setText("已复制到剪贴板")

    def clipboard(self):
        from PyQt5.QtWidgets import QApplication
        return QApplication.instance().clipboard()

    def closeEvent(self, event):
        try:
            if self._worker and self._worker.isRunning():
                self._worker.finished.disconnect()
                self._worker.error.disconnect()
                self._worker.terminate()
        except Exception:
            pass
        super().closeEvent(event)

    # Public helper for external callers
    def start_with_text(self, text: str, auto: bool = True):
        try:
            self.input_edit.setPlainText(text or "")
            if auto:
                self._on_learn_clicked()
        except Exception:
            pass
