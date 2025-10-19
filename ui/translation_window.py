"""
Translation window implementation for the OCR translator application.
"""
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QLabel, QTextEdit, QPushButton, QFrame, QHBoxLayout, 
                           QStatusBar, QMessageBox, QShortcut)
from PyQt5.QtCore import Qt, QPoint, QTimer, QPropertyAnimation
from PyQt5.QtGui import QFont, QPalette, QColor, QKeySequence, QTextOption

import time
try:
    from .ai_study_dialog import AIStudyDialog
except Exception:
    try:
        from ui.ai_study_dialog import AIStudyDialog
    except Exception:
        AIStudyDialog = None

class TranslationWindow(QMainWindow):
    def __init__(self, translated_text, source_text, source_lang, target_lang, pos_x, pos_y, width, height, original_coords=None):
        super().__init__()
        self.translated_text = translated_text
        self.source_text = source_text
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.pos_x = pos_x
        self.pos_y = pos_y
        self.width = width
        self.height = height
        self.original_coords = original_coords  # 保存原始选择区域坐标
        
        # 设置窗口标志 - 确保窗口置顶
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 初始化UI
        self.init_ui(pos_x, pos_y, width, height)
        
        # 鼠标拖动相关变量
        self.dragging = False
        self.drag_position = None
        
        # 设置淡出计时器
        self.fade_timer = QTimer(self)
        self.fade_timer.timeout.connect(self.fade_out)
        
        # 显示窗口并确保置顶
        self.show()
        self.activateWindow()
        self.raise_()
        
        try:
            # 增强的淡入动画
            self.setWindowOpacity(0.0)
            self.animation = QPropertyAnimation(self, b"windowOpacity")
            self.animation.setDuration(300)  # 稍微延长动画时间，使其更流畅
            self.animation.setStartValue(0.0)
            self.animation.setEndValue(1.0)
            self.animation.start()
        except Exception as e:
            print(f"淡入动画初始化失败: {e}")
            self.setWindowOpacity(1.0)  # 确保窗口可见
        
        # 跟踪鼠标活动
        self.setMouseTracking(True)
        self.last_activity = time.time()
    
    def init_ui(self, pos_x, pos_y, width, height):
        # 设置窗口标题和基本属性
        self.setWindowTitle("翻译结果")
        
        # 设置窗口大小和位置
        self.resize(width, height)
        self.move(pos_x, pos_y)
        
        # 创建中心部件和布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(15, 15, 15, 15)  # 保持外边距以显示阴影
        
        # 设置现代化主题样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: transparent;
            }
            QWidget#mainContainer {
                background-color: rgba(25, 25, 25, 0.97);
                border: 1px solid #444444;
                border-radius: 12px;
            }
            QWidget#contentContainer {
                background-color: transparent;
                border-radius: 10px;
            }
            QLabel {
                color: #ffffff;
                padding: 5px;
                background: transparent;
                font-family: "Segoe UI", Arial, sans-serif;
            }
            QTextEdit {
                background-color: rgba(40, 40, 40, 0.7);
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 12px;
                selection-background-color: #2979ff;
                font-family: "Segoe UI", Arial, sans-serif;
                font-size: 13px;
            }
            QTextEdit:focus {
                border: 1px solid #2979ff;
                background-color: rgba(40, 40, 40, 0.9);
            }
            QPushButton {
                background-color: #2979ff;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 18px;
                font-weight: bold;
                min-width: 90px;
                margin: 3px;
                font-family: "Segoe UI", Arial, sans-serif;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #3d8aff;
                border: 1px solid #5d9aff;
            }
            QPushButton:pressed {
                background-color: #1c68e3;
            }
            QPushButton#closeButton {
                background-color: transparent;
                color: #cccccc;
                min-width: 24px;
                padding: 0px;
                font-size: 18px;
                border-radius: 12px;
            }
            QPushButton#closeButton:hover {
                background-color: #ff4444;
                color: white;
            }
            QPushButton#minimizeButton {
                background-color: transparent;
                color: #cccccc;
                min-width: 24px;
                padding: 0px;
                font-size: 18px;
                border-radius: 12px;
            }
            QPushButton#minimizeButton:hover {
                background-color: #555555;
                color: white;
            }
            QFrame#separator {
                background-color: #444444;
                max-height: 1px;
                margin: 8px 0px;
            }
            QScrollBar:vertical {
                border: none;
                background: rgba(60, 60, 60, 0.5);
                width: 8px;
                margin: 0px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(150, 150, 150, 0.5);
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(180, 180, 180, 0.7);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
            QStatusBar {
                background: transparent;
                color: #999999;
                font-size: 11px;
                border: none;
            }
        """)
        
        # 创建主容器
        container = QWidget()
        container.setObjectName("mainContainer")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(2, 2, 2, 2)  # 减小内边距
        container_layout.setSpacing(5)  # 减小组件间距
        
        # 创建内容容器
        content = QWidget()
        content.setObjectName("contentContainer")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(12, 12, 12, 12)
        container_layout.addWidget(content)
        
        # 添加标题栏
        title_bar = QWidget()
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(5, 5, 5, 5)
        
        # 添加语言标识和图标
        title_label = QLabel(f"{self.source_lang} → {self.target_lang}")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #ffffff;")
        
        # 添加最小化按钮
        minimize_button = QPushButton("—")
        minimize_button.setObjectName("minimizeButton")
        minimize_button.setFixedSize(24, 24)
        minimize_button.clicked.connect(self.showMinimized)
        minimize_button.setToolTip("最小化")
        
        # 添加关闭按钮
        close_button = QPushButton("×")
        close_button.setObjectName("closeButton")
        close_button.setFixedSize(24, 24)
        close_button.clicked.connect(self.fade_out)
        close_button.setToolTip("关闭")
        
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        title_layout.addWidget(minimize_button)
        title_layout.addWidget(close_button)
        content_layout.addWidget(title_bar)
        
        # 添加分隔线
        separator = QFrame()
        separator.setObjectName("separator")
        separator.setFrameShape(QFrame.HLine)
        content_layout.addWidget(separator)
        
        # 添加原文区域
        source_label = QLabel("原文:")
        source_label.setStyleSheet("font-weight: bold; color: #cccccc; font-size: 13px;")
        content_layout.addWidget(source_label)
        
        self.source_text_edit = QTextEdit()
        # 保持段落格式，使用双换行符
        if self.source_text and "\n\n" in self.source_text:
            # 段落格式化文本 - 替换换行符为html格式
            formatted_text = self.source_text.replace("\n\n", "</p><p>")
            formatted_text = f"<p>{formatted_text}</p>"
            self.source_text_edit.setHtml(formatted_text)
        else:
            self.source_text_edit.setPlainText(self.source_text if self.source_text else "")
        self.source_text_edit.setReadOnly(True)
        self.source_text_edit.setMaximumHeight(120)  # 稍微增加高度
        self.source_text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        content_layout.addWidget(self.source_text_edit)
        
        # 添加译文区域
        target_label = QLabel("译文:")
        target_label.setStyleSheet("font-weight: bold; color: #cccccc; font-size: 13px;")
        content_layout.addWidget(target_label)
        
        self.translated_text_edit = QTextEdit()
        # 保持段落格式，使用双换行符
        if self.translated_text and "\n\n" in self.translated_text:
            # 段落格式化文本 - 替换换行符为html格式
            formatted_text = self.translated_text.replace("\n\n", "</p><p>")
            formatted_text = f"<p>{formatted_text}</p>"
            self.translated_text_edit.setHtml(formatted_text)
        else:
            self.translated_text_edit.setPlainText(self.translated_text)
        self.translated_text_edit.setReadOnly(True)
        self.translated_text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        content_layout.addWidget(self.translated_text_edit)
        
        # 添加按钮区域
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 8, 0, 0)
        
        copy_source_btn = QPushButton("复制原文 (O)")
        copy_source_btn.setIcon(self.style().standardIcon(self.style().SP_DialogSaveButton))
        copy_source_btn.setToolTip("复制原文到剪贴板 (快捷键: O)")
        
        copy_translated_btn = QPushButton("复制译文 (C)")
        copy_translated_btn.setIcon(self.style().standardIcon(self.style().SP_DialogSaveButton))
        copy_translated_btn.setToolTip("复制译文到剪贴板 (快捷键: C)")
        
        # 添加覆盖原文按钮
        overlay_btn = QPushButton("覆盖原文 (R)")
        overlay_btn.setIcon(self.style().standardIcon(self.style().SP_ArrowUp))
        overlay_btn.setToolTip("将译文覆盖到原始截图位置 (快捷键: R)")
        overlay_btn.setStyleSheet("""
            background-color: #ff9500;
            color: white;
        """)

        # 添加 AI学习 按钮（支持快捷键 A）
        ai_study_btn = QPushButton("AI学习 (A)")
        ai_study_btn.setToolTip("将原文发送到AI学习窗口并自动开始 (快捷键: A)")
        ai_study_btn.setStyleSheet("background-color: #2b67f6; color: white;")

        copy_source_btn.clicked.connect(self.copy_source_text)
        copy_translated_btn.clicked.connect(self.copy_translated_text)
        overlay_btn.clicked.connect(self.overlay_translated_text)
        ai_study_btn.clicked.connect(self.open_ai_study)

        button_layout.addWidget(copy_source_btn)
        button_layout.addWidget(copy_translated_btn)
        button_layout.addWidget(overlay_btn)
        button_layout.addWidget(ai_study_btn)
        content_layout.addWidget(button_container)
        
        # 添加状态栏
        status_label = QLabel("按ESC关闭窗口 | 按C复制译文 | 按O复制原文 | 按R覆盖原文 | 按A打开AI学习")
        status_label.setStyleSheet("""
            color: #999999;
            font-size: 11px;
            padding: 5px;
            margin-top: 5px;
        """)
        status_label.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(status_label)
        
        # 添加主容器到布局
        layout.addWidget(container)
        
        # 设置窗口可拖动
        self.old_pos = None
        title_bar.mousePressEvent = self.mousePressEvent
        title_bar.mouseMoveEvent = self.mouseMoveEvent
        
        # 添加键盘快捷键
        self.copy_source_shortcut = QShortcut(QKeySequence("O"), self)
        self.copy_source_shortcut.activated.connect(self.copy_source_text)

        self.copy_translated_shortcut = QShortcut(QKeySequence("C"), self)
        self.copy_translated_shortcut.activated.connect(self.copy_translated_text)

        # 添加覆盖原文快捷键
        self.overlay_shortcut = QShortcut(QKeySequence("R"), self)
        self.overlay_shortcut.activated.connect(self.overlay_translated_text)

        # 添加 AI学习 快捷键
        self.ai_study_shortcut = QShortcut(QKeySequence("A"), self)
        self.ai_study_shortcut.activated.connect(self.open_ai_study)
        
        self.close_shortcut = QShortcut(QKeySequence("Esc"), self)
        self.close_shortcut.activated.connect(self.fade_out)
        
        # 添加状态栏
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background: transparent;
                color: #999999;
                font-size: 11px;
                border: none;
            }
        """)
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("按ESC关闭窗口 | 按C复制译文 | 按O复制原文 | 按R覆盖原文 | 按A打开AI学习")

    def open_ai_study(self):
        try:
            # 复用全局 Translator 上的单例 AI学习 窗口
            parent = self.parent()
            if parent and hasattr(parent, 'show_ai_study_with_text'):
                parent.show_ai_study_with_text(self.source_text or "", True)
            else:
                # 回退：直接创建一次性窗口（不建议，保持兼容）
                if AIStudyDialog is None:
                    raise RuntimeError("AIStudyDialog 未就绪")
                dlg = AIStudyDialog(parent=self, initial_text=self.source_text or "", auto_start=True)
                dlg.show()
        except Exception as e:
            try:
                QMessageBox.warning(self, "AI学习", f"无法打开AI学习窗口: {e}")
            except Exception:
                print(f"无法打开AI学习窗口: {e}")
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.old_pos = event.globalPos()
    
    def mouseMoveEvent(self, event):
        if self.old_pos:
            delta = event.globalPos() - self.old_pos
            self.move(self.pos() + delta)
            self.old_pos = event.globalPos()
    
    def mouseReleaseEvent(self, event):
        self.old_pos = None
    
    def enterEvent(self, event):
        """鼠标进入窗口时的事件处理"""
        try:
            # 显示状态栏提示
            self.status_bar.showMessage("按ESC关闭窗口 | 按C复制译文 | 按O复制原文 | 按R覆盖原文 | 按A打开AI学习")
        except Exception as e:
            print(f"鼠标进入事件处理失败: {e}")
        
    def leaveEvent(self, event):
        """鼠标离开窗口时的事件处理"""
        pass  # 不做任何处理，移除自动隐藏功能
    
    def fade_out(self):
        """淡出并隐藏窗口"""
        try:
            # 创建淡出动画
            self.animation = QPropertyAnimation(self, b"windowOpacity")
            self.animation.setDuration(300)  # 300毫秒
            self.animation.setStartValue(1.0)
            self.animation.setEndValue(0.0)
            self.animation.finished.connect(self.hide)  # 改为hide而不是close
            self.animation.start()
        except Exception as e:
            print(f"淡出动画失败: {e}")
            self.hide()  # 直接隐藏窗口
    
    def copy_translated_text(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.translated_text)
        self.show_copy_animation(self.translated_text_edit)
    
    def copy_source_text(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.source_text if self.source_text else "")
        self.show_copy_animation(self.source_text_edit)
    
    def show_copy_animation(self, widget):
        """优化的复制动画效果"""
        try:
            original_style = widget.styleSheet()
            
            # 创建简单的颜色变化动画
            widget.setStyleSheet(original_style + "background-color: rgba(40, 180, 40, 0.3);")
            
            # 使用QTimer延迟恢复原样式
            def reset_style():
                widget.setStyleSheet(original_style)
                
            # 500毫秒后恢复原样式
            QTimer.singleShot(500, reset_style)
            
            # 在状态栏显示成功消息
            self.status_bar.showMessage("✓ 复制成功!", 2000)
            
        except Exception as e:
            # 如果动画失败，至少显示成功消息
            print(f"动画效果显示失败: {e}")
            self.status_bar.showMessage("复制成功!", 2000)

    # 添加覆盖原文的方法
    def overlay_translated_text(self):
        """将译文覆盖到原始截图位置"""
        try:
            # 通过信号调用OCRTranslator类的方法
            # 获取父对象的signals对象
            parent = self.parent()
            if parent and hasattr(parent, 'signals'):
                # 显示处理中的消息
                self.status_bar.showMessage("正在处理覆盖原文...", 2000)
                
                # 禁用所有按钮，防止重复点击
                for button in self.findChildren(QPushButton):
                    button.setEnabled(False)
                    button.setStyleSheet("background-color: #555555; color: #aaaaaa;")
                
                print("发送覆盖原文信号...")
                # 调试原始文本
                print(f"原始文本类型: {type(self.translated_text)}")
                print(f"原始文本内容: {self.translated_text}")
                print(f"原始文本编码点: {[ord(c) for c in self.translated_text]}")
                
                # 确保文本是Unicode格式
                translated_text = str(self.translated_text)
                
                # 调试转换后的文本
                print(f"转换后文本类型: {type(translated_text)}")
                print(f"转换后文本内容: {translated_text}")
                
                # 使用原始选择区域坐标（如果有）
                if self.original_coords and len(self.original_coords) == 4:
                    x, y, w, h = self.original_coords
                    print(f"使用原始选择区域坐标: x={x}, y={y}, w={w}, h={h}")
                    # 发送信号
                    parent.signals.overlay_text.emit(
                        translated_text,
                        x,
                        y,
                        w,
                        h
                    )
                else:
                    # 如果没有原始坐标，使用当前窗口位置和大小
                    print(f"警告：没有原始选择区域坐标，使用当前窗口位置和大小")
                    print(f"窗口位置和大小: x={self.pos_x}, y={self.pos_y}, w={self.width}, h={self.height}")
                    # 发送信号
                    parent.signals.overlay_text.emit(
                        translated_text,
                        self.pos_x,
                        self.pos_y,
                        self.width,
                        self.height
                    )
                
                # 显示成功消息
                self.status_bar.showMessage("✓ 已将译文覆盖到原图!", 1000)
                
                # 使用QTimer延迟关闭窗口，确保信号处理完成
                print("设置延迟关闭窗口...")
                QTimer.singleShot(1500, self.fade_out)
            else:
                raise Exception("无法获取父对象或信号对象")
            
        except Exception as e:
            print(f"覆盖原文失败: {e}")
            self.status_bar.showMessage("❌ 覆盖原文失败!", 2000)
            
            # 重新启用按钮
            for button in self.findChildren(QPushButton):
                button.setEnabled(True)
                button.setStyleSheet("")  # 恢复默认样式

    def update_settings(self, settings):
        """更新窗口设置"""
        if "OVERLAY_FONT_SIZE" in settings:
            font = self.source_text_edit.font()
            font.setPointSize(settings["OVERLAY_FONT_SIZE"])
            self.source_text_edit.setFont(font)
            self.translated_text_edit.setFont(font)
        
        if "OVERLAY_PADDING" in settings:
            content = self.findChild(QWidget, "contentContainer")
            if content:
                content.layout().setContentsMargins(
                    settings["OVERLAY_PADDING"],
                    settings["OVERLAY_PADDING"],
                    settings["OVERLAY_PADDING"],
                    settings["OVERLAY_PADDING"]
                )
        
        if "OVERLAY_LINE_SPACING" in settings:
            self.source_text_edit.document().setDocumentMargin(settings["OVERLAY_LINE_SPACING"])
            self.translated_text_edit.document().setDocumentMargin(settings["OVERLAY_LINE_SPACING"])
        
        if "OVERLAY_TEXT_SPACING" in settings:
            self.set_text_line_spacing(settings["OVERLAY_TEXT_SPACING"])
        
        if "OVERLAY_TEXT_ALIGNMENT" in settings:
            alignment = {
                "left": Qt.AlignLeft,
                "center": Qt.AlignCenter,
                "right": Qt.AlignRight
            }.get(settings["OVERLAY_TEXT_ALIGNMENT"], Qt.AlignLeft)
            self.source_text_edit.setAlignment(alignment)
            self.translated_text_edit.setAlignment(alignment)
        
        if "OVERLAY_FONT_WEIGHT" in settings:
            font = self.source_text_edit.font()
            font.setWeight(QFont.Bold if settings["OVERLAY_FONT_WEIGHT"] == "bold" else QFont.Normal)
            self.source_text_edit.setFont(font)
            self.translated_text_edit.setFont(font)
            
    def set_text_line_spacing(self, spacing):
        """设置文本行间距"""
        for text_edit in [self.source_text_edit, self.translated_text_edit]:
            text_option = QTextOption(text_edit.document().defaultTextOption())
            text_option.setLineHeight(spacing * 100, QTextOption.ProportionalHeight)
            text_edit.document().setDefaultTextOption(text_option)
