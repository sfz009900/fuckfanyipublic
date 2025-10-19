from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QLabel, QTextEdit, QPushButton, QFrame, QHBoxLayout, 
                           QStatusBar, QMessageBox, QShortcut, QGraphicsOpacityEffect,
                           QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView,
                           QDialog, QSplitter, QAbstractItemView, QTabWidget, QGroupBox,
                           QFormLayout, QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox, QSlider,
                           QColorDialog, QCheckBox)
from PyQt5.QtCore import (Qt, QPoint, QTimer, pyqtSignal, QObject, 
                         QPropertyAnimation, QSize, QDate, QDateTime)
from PyQt5.QtGui import (QFont, QPalette, QColor, QKeySequence, QImage, QPixmap)

class AboutDialog(QDialog):
    """关于对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("关于 OCR Translator")
        self.setFixedSize(500, 400)
        self.setStyleSheet("""
            QDialog {
                background-color: white;
            }
            QLabel {
                color: #2c3e50;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        
        # 创建布局
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Logo标签
        logo_label = QLabel()
        # 这里可以设置实际的logo
        # logo_label.setPixmap(QPixmap("path/to/logo.png").scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo_label.setFixedSize(100, 100)
        logo_label.setStyleSheet("background-color: #f0f0f0; border-radius: 10px;")
        logo_label.setAlignment(Qt.AlignCenter)
        
        # 标题标签
        title_label = QLabel("OCR Translator")
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        
        # 版本标签
        version_label = QLabel("版本 1.0.0")
        version_label.setAlignment(Qt.AlignCenter)
        version_font = QFont()
        version_font.setPointSize(10)
        version_label.setFont(version_font)
        
        # 描述标签
        desc_label = QLabel(
            "OCR Translator 是一个强大的屏幕翻译工具，支持实时OCR识别和多种翻译引擎。\n"
            "它能够帮助您快速翻译屏幕上的任何文本内容，提供高效的翻译体验。"
        )
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setStyleSheet("color: #7f8c8d; margin: 10px;")
        
        # 官网链接
        website_label = QLabel('<a href="https://github.com/sfz009900/ocrtotext" style="color: #3498db; text-decoration: none;">访问官方网站</a>')
        website_label.setOpenExternalLinks(True)
        website_label.setAlignment(Qt.AlignCenter)
        
        # 版权信息
        copyright_label = QLabel("© 2024 OCR Translator Team. All rights reserved.")
        copyright_label.setAlignment(Qt.AlignCenter)
        copyright_label.setStyleSheet("color: #95a5a6; font-size: 9pt;")
        
        # 添加组件到布局
        layout.addWidget(logo_label, alignment=Qt.AlignCenter)
        layout.addWidget(title_label)
        layout.addWidget(version_label)
        layout.addSpacing(10)
        layout.addWidget(desc_label)
        layout.addSpacing(10)
        layout.addWidget(website_label)
        layout.addSpacing(20)
        layout.addWidget(copyright_label)
        layout.addStretch()
        
        # 确定按钮
        ok_button = QPushButton("确定")
        ok_button.setFixedWidth(120)
        ok_button.clicked.connect(self.accept)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        button_layout.addStretch()
        
        # 添加按钮布局
        layout.addLayout(button_layout)
        
        # 设置对话框布局
        self.setLayout(layout)