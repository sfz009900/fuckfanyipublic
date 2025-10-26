from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout


class HintBubble(QDialog):
    def __init__(self, message: str, on_start=None, parent=None, duration_ms: int = 4000):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.on_start = on_start

        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        card = QVBoxLayout()
        wrapper = QLabel()
        wrapper.setStyleSheet("background: rgba(17,24,39,0.92); border-radius: 10px;")
        lay.addWidget(wrapper)
        # Overlay content on top of wrapper
        inner = QVBoxLayout(wrapper)
        text = QLabel(message)
        text.setStyleSheet("color:#e5e7eb; padding:10px; font-size:13px;")
        inner.addWidget(text)
        row = QHBoxLayout()
        btn = QPushButton("开始")
        btn.setStyleSheet("QPushButton{background:#22c55e;color:#062; border:none; border-radius:6px; padding:6px 10px; font-weight:700;} QPushButton:hover{background:#16a34a;color:white}")
        btn.clicked.connect(self._start)
        row.addStretch(); row.addWidget(btn)
        inner.addLayout(row)

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.accept)
        self.timer.start(max(1500, duration_ms))

    def _start(self):
        if callable(self.on_start):
            try:
                self.on_start()
            except Exception:
                pass
        self.accept()

