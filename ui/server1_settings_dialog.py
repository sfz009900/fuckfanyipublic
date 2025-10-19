from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, 
                           QLabel, QComboBox, QPushButton, QHBoxLayout)
from PyQt5.QtCore import Qt

class Server1SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("测试服务器1设置")
        self.resize(400, 200)
        
        # 创建主布局
        layout = QVBoxLayout()
        form_layout = QFormLayout()
        
        # 翻译模型（不可更改）
        self.model_label = QLabel("gemma2:27b")
        self.model_label.setEnabled(False)
        form_layout.addRow("翻译模型:", self.model_label)
        
        # 场景选择
        self.scene_combo = QComboBox()
        self.scene_combo.addItem("推特模式", 1)
        self.scene_combo.addItem("普通模式", 2)
        form_layout.addRow("场景选择:", self.scene_combo)
        
        # 添加表单布局
        layout.addLayout(form_layout)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("确定")
        self.cancel_button = QPushButton("取消")
        
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def get_settings(self):
        """获取设置值"""
        return {
            'model': 'gemma2:27b',
            'scene': self.scene_combo.currentData()
        }
    
    def set_settings(self, scene):
        """设置当前值"""
        index = self.scene_combo.findData(scene)
        if index >= 0:
            self.scene_combo.setCurrentIndex(index) 