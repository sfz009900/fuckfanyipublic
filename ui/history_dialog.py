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

class HistoryDialog(QDialog):
    """翻译历史记录对话框"""
    def __init__(self, history_list, parent=None):
        super().__init__(parent)
        self.history_list = history_list
        self.selected_translation = None
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("翻译历史记录")
        self.setMinimumSize(700, 500)
        
        # 创建主布局
        layout = QVBoxLayout()
        
        # 创建表格
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["时间", "原文", "译文", "语言对"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        
        # 加载历史记录数据
        self.load_data()
        
        # 创建按钮布局
        btn_layout = QHBoxLayout()
        
        # 创建复制按钮
        copy_btn = QPushButton("复制所选译文")
        copy_btn.clicked.connect(self.copy_translation)
        
        # 创建清空按钮
        clear_btn = QPushButton("清空历史记录")
        clear_btn.clicked.connect(self.clear_history)
        
        # 创建关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        
        # 添加按钮到布局
        btn_layout.addWidget(copy_btn)
        btn_layout.addWidget(clear_btn)
        btn_layout.addWidget(close_btn)
        
        # 添加控件到主布局
        layout.addWidget(self.table)
        layout.addLayout(btn_layout)
        
        # 设置对话框布局
        self.setLayout(layout)
        
    def load_data(self):
        """加载历史记录数据到表格"""
        self.table.setRowCount(len(self.history_list))
        
        for row, item in enumerate(reversed(self.history_list)):
            # 时间
            time_item = QTableWidgetItem(item['time'])
            self.table.setItem(row, 0, time_item)
            
            # 原文（截断过长的文本）
            source_text = item['source_text']
            if len(source_text) > 100:
                source_text = source_text[:97] + "..."
            source_item = QTableWidgetItem(source_text)
            self.table.setItem(row, 1, source_item)
            
            # 译文（截断过长的文本）
            translated_text = item['translated_text']
            if len(translated_text) > 100:
                translated_text = translated_text[:97] + "..."
            trans_item = QTableWidgetItem(translated_text)
            self.table.setItem(row, 2, trans_item)
            
            # 语言对
            lang_pair = f"{item['source_lang']} → {item['target_lang']}"
            lang_item = QTableWidgetItem(lang_pair)
            self.table.setItem(row, 3, lang_item)
        
    def copy_translation(self):
        """复制所选翻译到剪贴板"""
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "提示", "请先选择一条翻译记录")
            return
        
        row = selected_rows[0].row()
        text = self.history_list[len(self.history_list) - 1 - row]['translated_text']
        
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        
        QMessageBox.information(self, "成功", "已复制译文到剪贴板")
    
    def clear_history(self):
        """清空历史记录"""
        reply = QMessageBox.question(self, "确认", "确定要清空所有历史记录吗？",
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.history_list.clear()
            self.table.setRowCount(0)
            QMessageBox.information(self, "成功", "历史记录已清空")