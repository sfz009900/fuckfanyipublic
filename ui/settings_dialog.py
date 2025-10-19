from PyQt5.QtWidgets import (QDialog, QWidget, QVBoxLayout, QHBoxLayout, 
                           QLabel, QTextEdit, QPushButton, QFrame, QStatusBar, QMessageBox, 
                           QShortcut, QGraphicsOpacityEffect, QFileDialog, QTableWidget, 
                           QTableWidgetItem, QHeaderView, QSplitter, QAbstractItemView, 
                           QTabWidget, QGroupBox, QFormLayout, QComboBox, QLineEdit, 
                           QSpinBox, QDoubleSpinBox, QSlider, QColorDialog, QCheckBox,
                           QScrollArea)
from PyQt5.QtCore import (Qt, QPoint, QTimer, pyqtSignal, QObject, 
                         QPropertyAnimation, QSize, QDate, QDateTime)
from PyQt5.QtGui import (QFont, QPalette, QColor, QKeySequence, QImage, QPixmap)
from ui.image_display_window import ImageDisplayWindow
from ui.translation_window import TranslationWindow
from ui.history_dialog import HistoryDialog
from ui.server1_settings_dialog import Server1SettingsDialog
from config_manager import config
import requests
import json

class SettingsDialog(QDialog):
    """设置对话框"""
    # 添加设置变更信号
    settings_changed = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        """初始化设置对话框"""
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.resize(600, 800)  # 增加默认窗口大小
        
        # 创建主布局
        main_layout = QVBoxLayout()
        
        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # 创建容器widget
        container = QWidget()
        container_layout = QVBoxLayout()
        
        # 创建选项卡部件
        self.tab_widget = QTabWidget()
        
        # 创建各个选项卡时直接使用实例变量
        self.general_tab = QWidget()
        self.ocr_tab = QWidget()  # 直接创建实例变量
        self.ui_tab = QWidget()
        
        # 初始化各个选项卡
        self.init_general_tab()
        self.init_ocr_tab()  # 改为无返回值的初始化方法
        self.init_ui_tab()
        
        # 添加选项卡
        self.tab_widget.addTab(self.general_tab, "常规")
        self.tab_widget.addTab(self.ocr_tab, "OCR")
        self.tab_widget.addTab(self.ui_tab, "界面")
        
        # 将选项卡添加到容器布局
        container_layout.addWidget(self.tab_widget)
        container.setLayout(container_layout)
        
        # 将容器添加到滚动区域
        scroll.setWidget(container)
        
        # 创建按钮布局
        button_box = QHBoxLayout()
        save_btn = QPushButton("保存")
        cancel_btn = QPushButton("取消")
        save_btn.clicked.connect(self.save_settings)
        cancel_btn.clicked.connect(self.reject)
        button_box.addStretch()
        button_box.addWidget(save_btn)
        button_box.addWidget(cancel_btn)
        
        # 添加滚动区域和按钮到主布局
        main_layout.addWidget(scroll)
        main_layout.addLayout(button_box)
        
        self.setLayout(main_layout)
    
    def init_general_tab(self):
        """初始化常规选项卡"""
        layout = QVBoxLayout()
        
        # 源语言和目标语言设置
        lang_group = QGroupBox("语言设置")
        lang_layout = QFormLayout()
        
        # 源语言
        self.source_lang_combo = QComboBox()
        self.source_lang_combo.addItems(["en", "zh-CN", "ja", "ko", "fr", "de", "es"])
        self.source_lang_combo.setCurrentText(config.get('OCR_TRANSLATION', 'source_language'))
        lang_layout.addRow("源语言:", self.source_lang_combo)
        
        # 目标语言
        self.target_lang_combo = QComboBox()
        self.target_lang_combo.addItems(["zh-CN", "en", "ja", "ko", "fr", "de", "es"])
        self.target_lang_combo.setCurrentText(config.get('OCR_TRANSLATION', 'target_language'))
        lang_layout.addRow("目标语言:", self.target_lang_combo)
        
        # 热键设置
        self.screenshot_hotkey_edit = QLineEdit(config.get('HOTKEYS', 'screenshot_hotkey'))
        lang_layout.addRow("截图热键:", self.screenshot_hotkey_edit)
        
        # 复制和关闭热键
        self.copy_key_edit = QLineEdit(config.get('HOTKEYS', 'copy_key'))
        self.close_key_edit = QLineEdit(config.get('HOTKEYS', 'close_key'))
        lang_layout.addRow("复制热键:", self.copy_key_edit)
        lang_layout.addRow("关闭热键:", self.close_key_edit)
        
        lang_group.setLayout(lang_layout)
        
        # 翻译引擎设置
        engine_group = QGroupBox("翻译引擎设置")
        engine_layout = QFormLayout()
        
        # 翻译引擎选择
        self.translation_engine_combo = QComboBox()
        self.translation_engine_combo.addItems([
            "ollama", "openai", "测试服务器1", "谷歌翻译", "微软翻译", "可腾翻译",
            "niutrans", "mymemory", "alibaba", "baidu", "modernmt",
            "volcengine", "iciba", "iflytek", "google", "bing", "lingvanex",
            "yandex", "itranslate", "systran", "argos", "apertium", "reverso",
            "deepl", "qqtransmart", "translatecom", "sogou", "tilde", "caiyun",
            "qqfanyi", "translateme", "papago", "mirai", "youdao", "iflyrec",
            "hujiang", "yeekit", "languagewire", "elia", "judic", "mglip",
            "utibet", "cloudtranslation"
        ])
        self.translation_engine_combo.setCurrentText(config.get('OCR_TRANSLATION', 'translation_engine'))
        self.translation_engine_combo.currentTextChanged.connect(self.on_translation_engine_changed)
        engine_layout.addRow("翻译引擎:", self.translation_engine_combo)
        
        # API URL
        self.api_url_edit = QLineEdit(config.get('OCR_TRANSLATION', 'api_url'))
        self.api_url_label = QLabel("API URL:")
        engine_layout.addRow(self.api_url_label, self.api_url_edit)
        
        # OpenAI API Key
        self.openai_key_edit = QLineEdit(config.get('OCR_TRANSLATION', 'openai_api_key', fallback=''))
        self.openai_key_label = QLabel("OpenAI API Key:")
        engine_layout.addRow(self.openai_key_label, self.openai_key_edit)
        
        # 模型选择
        self.translation_model_edit = QLineEdit(config.get('OCR_TRANSLATION', 'translation_model'))
        self.translation_model_label = QLabel("翻译模型:")
        engine_layout.addRow(self.translation_model_label, self.translation_model_edit)
        
        # 服务器1设置按钮
        self.server1_settings_btn = QPushButton("设置")
        self.server1_settings_btn.clicked.connect(self.show_server1_settings)
        self.server1_settings_label = QLabel("服务器1设置:")
        engine_layout.addRow(self.server1_settings_label, self.server1_settings_btn)
        
        # Temperature设置
        self.temperature_spinbox = QDoubleSpinBox()
        self.temperature_spinbox.setRange(0.0, 2.0)
        self.temperature_spinbox.setSingleStep(0.1)
        self.temperature_spinbox.setValue(config.get('OCR_TRANSLATION', 'temperature', 0.3))
        self.temperature_label = QLabel("Temperature:")
        engine_layout.addRow(self.temperature_label, self.temperature_spinbox)
        
        # 根据当前引擎设置控件的可见性
        self.update_engine_controls_visibility()
        
        # 翻译提示词
        self.translation_prompt_edit = QTextEdit()
        self.translation_prompt_edit.setPlainText(config.get('OCR_TRANSLATION', 'translation_prompt'))
        self.translation_prompt_edit.setMaximumHeight(100)
        
        # 提示词管理
        self.prompt_presets_combo = QComboBox()
        self.prompt_presets_combo.currentIndexChanged.connect(self.on_preset_selected)
        self.preset_notes_edit = QTextEdit()
        self.preset_notes_edit.setMaximumHeight(40)
        self.preset_notes_edit.setReadOnly(True)
        
        # 管理按钮
        manage_btn_layout = QHBoxLayout()
        self.add_preset_btn = QPushButton("新增")
        self.edit_preset_btn = QPushButton("编辑")
        self.del_preset_btn = QPushButton("删除")
        self.add_preset_btn.clicked.connect(self.add_prompt_preset)
        self.edit_preset_btn.clicked.connect(self.edit_prompt_preset)
        self.del_preset_btn.clicked.connect(self.del_prompt_preset)
        
        manage_btn_layout.addWidget(self.add_preset_btn)
        manage_btn_layout.addWidget(self.edit_preset_btn)
        manage_btn_layout.addWidget(self.del_preset_btn)
        
        engine_layout.addRow("预设提示词:", self.prompt_presets_combo)
        engine_layout.addRow("预设说明:", self.preset_notes_edit)
        engine_layout.addRow("管理预设:", manage_btn_layout)
        
        # 添加提示说明标签
        prompt_hint = QLabel("ollama示例:翻译{source_lang}为{target_lang}待翻译文本为:{text}\r\n openai示例:翻译{source_lang}为{target_lang}")
        prompt_hint.setStyleSheet("color: gray;")
        engine_layout.addRow("", prompt_hint)
        
        engine_group.setLayout(engine_layout)
        
        # 添加组到布局
        layout.addWidget(lang_group)
        layout.addWidget(engine_group)
        layout.addStretch()
        
        # 设置布局
        self.general_tab.setLayout(layout)
    
    def init_ocr_tab(self):
        """初始化OCR设置选项卡"""
        layout = QVBoxLayout(self.ocr_tab)  # 直接设置布局到实例变量
        
        # OCR基本设置组
        ocr_group = QGroupBox("OCR设置")
        ocr_layout = QFormLayout()
        
        # OCR语言选择
        self.ocr_lang_combo = QComboBox()
        languages = {
            "ch": "zh-CN",
            "en": "en",
            "fr": "法语",
            "german": "德语",
            "korean": "韩语",
            "japan": "日语"
        }
        for code, name in languages.items():
            self.ocr_lang_combo.addItem(name, code)
        # 设置当前语言
        current_lang = config.get('PADDLEOCR', 'ocr_language')
        index = self.ocr_lang_combo.findData(current_lang)
        if index >= 0:
            self.ocr_lang_combo.setCurrentIndex(index)
        ocr_layout.addRow("OCR语言:", self.ocr_lang_combo)
        
        # OCR高级设置
        self.use_angle_cls_check = QCheckBox()
        self.use_angle_cls_check.setChecked(config.get('PADDLEOCR', 'ocr_use_angle_cls'))
        ocr_layout.addRow("使用方向分类器:", self.use_angle_cls_check)
        
        self.use_gpu_check = QCheckBox()
        self.use_gpu_check.setChecked(config.get('PADDLEOCR', 'ocr_use_gpu'))
        ocr_layout.addRow("使用GPU:", self.use_gpu_check)
        
        self.enable_mkldnn_check = QCheckBox()
        self.enable_mkldnn_check.setChecked(config.get('PADDLEOCR', 'ocr_enable_mkldnn'))
        ocr_layout.addRow("启用MKL-DNN加速:", self.enable_mkldnn_check)
        
        self.show_log_check = QCheckBox()
        self.show_log_check.setChecked(config.get('PADDLEOCR', 'ocr_show_log'))
        ocr_layout.addRow("显示日志:", self.show_log_check)
        
        # OCR超时设置
        self.ocr_timeout_spinbox = QSpinBox()
        self.ocr_timeout_spinbox.setRange(1, 120)
        self.ocr_timeout_spinbox.setValue(config.get('PADDLEOCR', 'ocr_timeout'))
        self.ocr_timeout_spinbox.setSuffix(" 秒")
        ocr_layout.addRow("OCR超时时间:", self.ocr_timeout_spinbox)
        
        ocr_group.setLayout(ocr_layout)
        layout.addWidget(ocr_group)
        
        # 图像预处理设置组
        preprocess_group = QGroupBox("图像预处理")
        preprocess_layout = QFormLayout()
        
        # 启用预处理
        self.enable_preprocessing_check = QCheckBox()
        self.enable_preprocessing_check.setChecked(config.get('IMAGE_PROCESSING', 'enable_preprocessing'))
        preprocess_layout.addRow("启用预处理:", self.enable_preprocessing_check)
        
        # 降噪强度
        self.denoise_spinbox = QSpinBox()
        self.denoise_spinbox.setRange(0, 100)
        self.denoise_spinbox.setValue(config.get('IMAGE_PROCESSING', 'denoise_strength'))
        preprocess_layout.addRow("降噪强度:", self.denoise_spinbox)
        
        # 对比度增强
        self.contrast_spinbox = QDoubleSpinBox()
        self.contrast_spinbox.setRange(0.1, 3.0)
        self.contrast_spinbox.setSingleStep(0.1)
        self.contrast_spinbox.setValue(config.get('IMAGE_PROCESSING', 'contrast_alpha'))
        preprocess_layout.addRow("对比度增强:", self.contrast_spinbox)
        
        preprocess_group.setLayout(preprocess_layout)
        layout.addWidget(preprocess_group)
        
        # 添加弹性空间
        layout.addStretch()
        
        self.ocr_tab.setLayout(layout)
    
    def init_ui_tab(self):
        """初始化UI选项卡"""
        layout = QVBoxLayout()
        
        # 用户界面设置
        ui_group = QGroupBox("用户界面设置")
        ui_layout = QFormLayout()
        
        # 选择框颜色
        self.selection_color_btn = QPushButton()
        self.selection_color_btn.setStyleSheet(f"background-color: rgb{config.get('UI', 'selection_color')}; min-width: 30px;")
        self.selection_color_btn.clicked.connect(self.choose_selection_color)
        ui_layout.addRow("选择框颜色:", self.selection_color_btn)
        
        # 指示器颜色
        self.guide_color_btn = QPushButton()
        self.guide_color_btn.setStyleSheet(f"background-color: rgb{config.get('UI', 'guide_color')}; min-width: 30px;")
        self.guide_color_btn.clicked.connect(self.choose_guide_color)
        ui_layout.addRow("指示器颜色:", self.guide_color_btn)
        
        # 十字线颜色
        self.crosshair_color_btn = QPushButton()
        self.crosshair_color_btn.setStyleSheet(f"background-color: rgb{config.get('UI', 'crosshair_color')}; min-width: 30px;")
        self.crosshair_color_btn.clicked.connect(self.choose_crosshair_color)
        ui_layout.addRow("十字线颜色:", self.crosshair_color_btn)
        
        # 十字线大小
        self.crosshair_size_spinbox = QSpinBox()
        self.crosshair_size_spinbox.setRange(10, 50)
        self.crosshair_size_spinbox.setValue(config.get('UI', 'crosshair_size'))
        ui_layout.addRow("十字线大小:", self.crosshair_size_spinbox)
        
        # 十字线粗细
        self.crosshair_thickness_spinbox = QSpinBox()
        self.crosshair_thickness_spinbox.setRange(1, 5)
        self.crosshair_thickness_spinbox.setValue(config.get('UI', 'crosshair_thickness'))
        ui_layout.addRow("十字线粗细:", self.crosshair_thickness_spinbox)
        
        # 覆盖层透明度
        self.overlay_opacity_slider = QSlider(Qt.Horizontal)
        self.overlay_opacity_slider.setRange(0, 255)
        self.overlay_opacity_slider.setValue(config.get('UI', 'overlay_opacity'))
        ui_layout.addRow("覆盖层透明度:", self.overlay_opacity_slider)
        
        # 字体大小
        self.font_size_spinbox = QSpinBox()
        self.font_size_spinbox.setRange(8, 48)
        self.font_size_spinbox.setValue(config.get('UI', 'font_size'))
        ui_layout.addRow("字体大小:", self.font_size_spinbox)
        
        # 字体颜色
        self.font_color_btn = QPushButton()
        self.font_color_btn.setStyleSheet(f"background-color: rgb{config.get('UI', 'font_color')}; min-width: 30px;")
        self.font_color_btn.clicked.connect(self.choose_font_color)
        ui_layout.addRow("字体颜色:", self.font_color_btn)
        
        # 背景颜色
        self.background_color_btn = QPushButton()
        self.background_color_btn.setStyleSheet(f"background-color: rgb{config.get('UI', 'background_color')}; min-width: 30px;")
        self.background_color_btn.clicked.connect(self.choose_background_color)
        ui_layout.addRow("背景颜色:", self.background_color_btn)
        
        ui_group.setLayout(ui_layout)
        
        # 覆盖层设置组
        overlay_group = QGroupBox("覆盖层设置")
        overlay_layout = QFormLayout()
        
        # 覆盖层背景颜色
        self.overlay_bg_color_btn = QPushButton()
        self.overlay_bg_color_btn.setStyleSheet(f"background-color: rgba{config.get('OVERLAY', 'overlay_bg_color')}; min-width: 30px;")
        self.overlay_bg_color_btn.clicked.connect(self.choose_overlay_bg_color)
        overlay_layout.addRow("覆盖层背景颜色:", self.overlay_bg_color_btn)
        
        # 覆盖层文本颜色
        self.overlay_text_color_btn = QPushButton()
        self.overlay_text_color_btn.setStyleSheet(f"background-color: rgba{config.get('OVERLAY', 'overlay_text_color')}; min-width: 30px;")
        self.overlay_text_color_btn.clicked.connect(self.choose_overlay_text_color)
        overlay_layout.addRow("覆盖层文本颜色:", self.overlay_text_color_btn)
        
        # 覆盖层字体大小
        self.overlay_font_size_spinbox = QSpinBox()
        self.overlay_font_size_spinbox.setRange(8, 48)
        self.overlay_font_size_spinbox.setValue(config.get('OVERLAY', 'overlay_font_size'))
        overlay_layout.addRow("覆盖层字体大小:", self.overlay_font_size_spinbox)
        
        # 覆盖层内边距
        self.overlay_padding_spinbox = QSpinBox()
        self.overlay_padding_spinbox.setRange(0, 50)
        self.overlay_padding_spinbox.setValue(config.get('OVERLAY', 'overlay_padding'))
        overlay_layout.addRow("覆盖层内边距:", self.overlay_padding_spinbox)
        
        # 覆盖层行间距
        self.overlay_line_spacing_spinbox = QSpinBox()
        self.overlay_line_spacing_spinbox.setRange(0, 20)
        self.overlay_line_spacing_spinbox.setValue(config.get('OVERLAY', 'overlay_line_spacing'))
        overlay_layout.addRow("行间距:", self.overlay_line_spacing_spinbox)
        
        # 覆盖层文本行间距
        self.overlay_text_spacing_spinbox = QDoubleSpinBox()
        self.overlay_text_spacing_spinbox.setRange(1.0, 3.0)
        self.overlay_text_spacing_spinbox.setSingleStep(0.1)
        self.overlay_text_spacing_spinbox.setValue(config.get('VISUAL_STYLE', 'OVERLAY_TEXT_SPACING', 1.2))
        overlay_layout.addRow("文本行间距:", self.overlay_text_spacing_spinbox)
        
        # 覆盖层最小字体大小
        self.overlay_min_font_size_spinbox = QSpinBox()
        self.overlay_min_font_size_spinbox.setRange(6, 24)
        self.overlay_min_font_size_spinbox.setValue(config.get('OVERLAY', 'overlay_min_font_size'))
        overlay_layout.addRow("最小字体大小:", self.overlay_min_font_size_spinbox)
        
        # 覆盖层自动扩展
        self.overlay_auto_expand_check = QCheckBox()
        self.overlay_auto_expand_check.setChecked(config.get('OVERLAY', 'overlay_auto_expand'))
        overlay_layout.addRow("自动扩展:", self.overlay_auto_expand_check)
        
        # 覆盖层文本对齐方式
        self.overlay_text_alignment_combo = QComboBox()
        self.overlay_text_alignment_combo.addItems(["left", "center", "right"])
        self.overlay_text_alignment_combo.setCurrentText(config.get('OVERLAY', 'overlay_text_alignment'))
        overlay_layout.addRow("文本对齐:", self.overlay_text_alignment_combo)
        
        # 覆盖层字体粗细
        self.overlay_font_weight_combo = QComboBox()
        self.overlay_font_weight_combo.addItems(["normal", "bold"])
        self.overlay_font_weight_combo.setCurrentText(config.get('OVERLAY', 'overlay_font_weight'))
        overlay_layout.addRow("字体粗细:", self.overlay_font_weight_combo)
        
        overlay_group.setLayout(overlay_layout)
        
        # 文本效果设置组
        text_effects_group = QGroupBox("文本效果")
        text_effects_layout = QFormLayout()
        
        # 文本描边宽度
        self.text_stroke_width_spinbox = QSpinBox()
        self.text_stroke_width_spinbox.setRange(0, 5)
        self.text_stroke_width_spinbox.setValue(config.get('TEXT_EFFECTS', 'text_stroke_width'))
        text_effects_layout.addRow("文本描边宽度:", self.text_stroke_width_spinbox)
        
        # 启用文本渐变
        self.text_gradient_check = QCheckBox()
        self.text_gradient_check.setChecked(config.get('TEXT_EFFECTS', 'text_gradient_enabled'))
        text_effects_layout.addRow("启用文本渐变:", self.text_gradient_check)
        
        # 启用背景模糊
        self.blur_enabled_check = QCheckBox()
        self.blur_enabled_check.setChecked(config.get('TEXT_EFFECTS', 'blur_enabled'))
        text_effects_layout.addRow("启用背景模糊:", self.blur_enabled_check)
        
        # 背景模糊半径
        self.blur_radius_spinbox = QSpinBox()
        self.blur_radius_spinbox.setRange(1, 50)
        self.blur_radius_spinbox.setValue(config.get('TEXT_EFFECTS', 'blur_radius'))
        text_effects_layout.addRow("模糊半径:", self.blur_radius_spinbox)
        
        # 启用背景渐变
        self.bg_gradient_check = QCheckBox()
        self.bg_gradient_check.setChecked(config.get('TEXT_EFFECTS', 'bg_gradient_enabled'))
        text_effects_layout.addRow("启用背景渐变:", self.bg_gradient_check)
        
        text_effects_group.setLayout(text_effects_layout)
        
        # 动画效果设置组
        animation_group = QGroupBox("动画效果")
        animation_layout = QFormLayout()
        
        # 启用动画
        self.animation_enabled_check = QCheckBox()
        self.animation_enabled_check.setChecked(config.get('ANIMATION_EFFECTS', 'animation_enabled'))
        animation_layout.addRow("启用动画:", self.animation_enabled_check)
        
        # 动画类型
        self.animation_type_combo = QComboBox()
        self.animation_type_combo.addItems(["slide", "fade", "scale"])
        self.animation_type_combo.setCurrentText(config.get('ANIMATION_EFFECTS', 'animation_type'))
        animation_layout.addRow("动画类型:", self.animation_type_combo)
        
        # 动画持续时间
        self.animation_duration_spinbox = QSpinBox()
        self.animation_duration_spinbox.setRange(100, 1000)
        self.animation_duration_spinbox.setValue(config.get('ANIMATION_EFFECTS', 'animation_duration'))
        self.animation_duration_spinbox.setSingleStep(50)
        self.animation_duration_spinbox.setSuffix(" ms")
        animation_layout.addRow("动画持续时间:", self.animation_duration_spinbox)
        
        animation_group.setLayout(animation_layout)
        
        # 添加组到布局
        layout.addWidget(ui_group)
        layout.addWidget(overlay_group)
        layout.addWidget(text_effects_group)
        layout.addWidget(animation_group)
        layout.addStretch()
        
        # 设置布局
        self.ui_tab.setLayout(layout)
    
    def choose_selection_color(self):
        """选择选择框颜色"""
        current_color = QColor(*config.get('UI', 'selection_color'))
        color = QColorDialog.getColor(current_color, self, "选择颜色")
        if color.isValid():
            self.selection_color_btn.setStyleSheet(f"background-color: {color.name()}; min-width: 30px;")
    
    def choose_guide_color(self):
        """选择指示器颜色"""
        current_color = QColor(*config.get('UI', 'guide_color'))
        color = QColorDialog.getColor(current_color, self, "选择颜色")
        if color.isValid():
            self.guide_color_btn.setStyleSheet(f"background-color: {color.name()}; min-width: 30px;")

    def choose_crosshair_color(self):
        """选择十字线颜色"""
        current_color = QColor(*config.get('UI', 'crosshair_color'))
        color = QColorDialog.getColor(current_color, self, "选择颜色")
        if color.isValid():
            self.crosshair_color_btn.setStyleSheet(f"background-color: {color.name()}; min-width: 30px;")

    def choose_font_color(self):
        """选择字体颜色"""
        current_color = QColor(*config.get('UI', 'font_color'))
        color = QColorDialog.getColor(current_color, self, "选择颜色")
        if color.isValid():
            self.font_color_btn.setStyleSheet(f"background-color: {color.name()}; min-width: 30px;")

    def choose_background_color(self):
        """选择背景颜色"""
        current_color = QColor(*config.get('UI', 'background_color'))
        color = QColorDialog.getColor(current_color, self, "选择颜色")
        if color.isValid():
            self.background_color_btn.setStyleSheet(f"background-color: {color.name()}; min-width: 30px;")

    def choose_overlay_bg_color(self):
        """选择覆盖层背景颜色"""
        current_color = QColor(*eval(config.get('OVERLAY', 'overlay_bg_color')))
        color = QColorDialog.getColor(current_color, self, "选择颜色", QColorDialog.ShowAlphaChannel)
        if color.isValid():
            self.overlay_bg_color_btn.setStyleSheet(f"background-color: rgba({color.red()},{color.green()},{color.blue()},{color.alpha()}); min-width: 30px;")

    def choose_overlay_text_color(self):
        """选择覆盖层文本颜色"""
        current_color = QColor(*eval(config.get('OVERLAY', 'overlay_text_color')))
        color = QColorDialog.getColor(current_color, self, "选择颜色", QColorDialog.ShowAlphaChannel)
        if color.isValid():
            self.overlay_text_color_btn.setStyleSheet(f"background-color: rgba({color.red()},{color.green()},{color.blue()},{color.alpha()}); min-width: 30px;")
    
    def update_engine_controls_visibility(self):
        """根据选择的翻译引擎更新控件可见性"""
        engine = self.translation_engine_combo.currentText()
        
        # OpenAI相关控件
        openai_visible = engine == "openai"
        self.openai_key_label.setVisible(openai_visible)
        self.openai_key_edit.setVisible(openai_visible)
        self.temperature_label.setVisible(openai_visible)
        self.temperature_spinbox.setVisible(openai_visible)
        
        # 测试服务器1相关控件
        server1_visible = engine == "测试服务器1"
        self.server1_settings_label.setVisible(server1_visible)
        self.server1_settings_btn.setVisible(server1_visible)
        self.translation_model_label.setVisible(not server1_visible)
        self.translation_model_edit.setVisible(not server1_visible)
        
        # API URL始终可见
        self.api_url_label.setVisible(True)
        self.api_url_edit.setVisible(True)

    def on_translation_engine_changed(self, engine):
        """当翻译引擎改变时调用"""
        self.update_engine_controls_visibility()
        
        if engine == "测试服务器1":
            self.translation_model_edit.setText("gemma2:27b")
            self.translation_model_edit.setEnabled(False)
        else:
            self.translation_model_edit.setEnabled(True)

    def show_server1_settings(self):
        """显示服务器1设置对话框"""
        dialog = Server1SettingsDialog(self)
        current_scene = config.get('OCR_TRANSLATION', 'scene', fallback=1)
        dialog.set_settings(current_scene)
        
        if dialog.exec_():
            settings = dialog.get_settings()
            self.translation_model_edit.setText(settings['model'])
            # 保存场景设置到配置中
            if not config.has_section('OCR_TRANSLATION'):
                config.add_section('OCR_TRANSLATION')
            config.set('OCR_TRANSLATION', 'scene', str(settings['scene']))
            config.save()

    def showEvent(self, event):
        """当对话框显示时重新加载预设"""
        super().showEvent(event)
        self.load_prompt_presets()
        self.on_translation_engine_changed(self.translation_engine_combo.currentText())
    
    def save_settings(self):
        """保存设置"""
        # 创建一个字典来存储所有设置
        settings = {
            'OCR_TRANSLATION': {
                'source_language': self.source_lang_combo.currentText(),
                'target_language': self.target_lang_combo.currentText(),
                'api_url': self.api_url_edit.text(),
                'translation_engine': self.translation_engine_combo.currentText(),
                'translation_model': self.translation_model_edit.text(),
                'translation_prompt': self.translation_prompt_edit.toPlainText(),
                'openai_api_key': self.openai_key_edit.text(),
                'temperature': self.temperature_spinbox.value(),
                'current_preset': self.prompt_presets_combo.currentText() if self.prompt_presets_combo.currentIndex() >=0 else '',
                'scene': config.get('OCR_TRANSLATION', 'scene', fallback=1)  # 保持场景设置
            },
            'HOTKEYS': {
                'screenshot_hotkey': self.screenshot_hotkey_edit.text(),
                'copy_key': self.copy_key_edit.text(),
                'close_key': self.close_key_edit.text()
            },
            'PADDLEOCR': {
                'ocr_language': self.ocr_lang_combo.currentData(),
                'ocr_use_angle_cls': self.use_angle_cls_check.isChecked(),
                'ocr_use_gpu': self.use_gpu_check.isChecked(),
                'ocr_enable_mkldnn': self.enable_mkldnn_check.isChecked(),
                'ocr_show_log': self.show_log_check.isChecked(),
                'ocr_timeout': self.ocr_timeout_spinbox.value()
            },
            'IMAGE_PROCESSING': {
                'enable_preprocessing': self.enable_preprocessing_check.isChecked(),
                'denoise_strength': self.denoise_spinbox.value(),
                'contrast_alpha': self.contrast_spinbox.value()
            },
            'UI': {
                'selection_color': eval(self.selection_color_btn.styleSheet().split('rgb')[1].split(';')[0]),
                'guide_color': eval(self.guide_color_btn.styleSheet().split('rgb')[1].split(';')[0]),
                'crosshair_color': eval(self.crosshair_color_btn.styleSheet().split('rgb')[1].split(';')[0]),
                'crosshair_size': self.crosshair_size_spinbox.value(),
                'crosshair_thickness': self.crosshair_thickness_spinbox.value(),
                'overlay_opacity': self.overlay_opacity_slider.value(),
                'font_size': self.font_size_spinbox.value(),
                'font_color': eval(self.font_color_btn.styleSheet().split('rgb')[1].split(';')[0]),
                'background_color': eval(self.background_color_btn.styleSheet().split('rgb')[1].split(';')[0])
            },
            'OVERLAY': {
                'overlay_bg_color': eval(self.overlay_bg_color_btn.styleSheet().split('rgba')[1].split(';')[0]),
                'overlay_text_color': eval(self.overlay_text_color_btn.styleSheet().split('rgba')[1].split(';')[0]),
                'overlay_font_size': self.overlay_font_size_spinbox.value(),
                'overlay_padding': self.overlay_padding_spinbox.value(),
                'overlay_line_spacing': self.overlay_line_spacing_spinbox.value(),
                'overlay_min_font_size': self.overlay_min_font_size_spinbox.value(),
                'overlay_auto_expand': self.overlay_auto_expand_check.isChecked(),
                'overlay_text_alignment': self.overlay_text_alignment_combo.currentText(),
                'overlay_font_weight': self.overlay_font_weight_combo.currentText()
            },
            'TEXT_EFFECTS': {
                'text_stroke_width': self.text_stroke_width_spinbox.value(),
                'text_gradient_enabled': self.text_gradient_check.isChecked(),
                'blur_enabled': self.blur_enabled_check.isChecked(),
                'blur_radius': self.blur_radius_spinbox.value(),
                'bg_gradient_enabled': self.bg_gradient_check.isChecked()
            },
            'ANIMATION_EFFECTS': {
                'animation_enabled': self.animation_enabled_check.isChecked(),
                'animation_type': self.animation_type_combo.currentText(),
                'animation_duration': self.animation_duration_spinbox.value()
            }
        }
        
        # 添加视觉样式设置
        settings['VISUAL_STYLE'] = {
            'OVERLAY_TEXT_SPACING': self.overlay_text_spacing_spinbox.value()
        }
        
        try:
            # Save settings to config.ini
            config.save_settings(settings)
            
            # 发送设置变更信号
            self.settings_changed.emit(settings)
            
            QMessageBox.information(self, "成功", "设置已保存并立即生效")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存设置时出错: {e}")

    def load_prompt_presets(self):
        """加载提示词预设"""
        self.prompt_presets_combo.clear()
        presets = config.get_prompt_presets()
        for name in presets.keys():
            self.prompt_presets_combo.addItem(name)
        
        # 设置当前选中的预设
        current_preset = config.get('OCR_TRANSLATION', 'current_preset', fallback='')
        if current_preset and current_preset in presets:
            index = self.prompt_presets_combo.findText(current_preset)
            self.prompt_presets_combo.setCurrentIndex(index)

    def on_preset_selected(self, index):
        """当选择预设时更新提示词编辑框"""
        if index >= 0:
            preset_name = self.prompt_presets_combo.currentText()
            presets = config.get_prompt_presets()
            self.translation_prompt_edit.setPlainText(presets[preset_name]['content'])
            self.preset_notes_edit.setPlainText(presets[preset_name].get('notes', ''))

    def add_prompt_preset(self):
        """添加新预设"""
        from ui.preset_dialog import PresetDialog
        dlg = PresetDialog(self)
        if dlg.exec_():
            name, content, notes = dlg.get_data()
            if name:
                config.add_prompt_preset(name, content, notes)
                self.load_prompt_presets()

    def edit_prompt_preset(self):
        """编辑当前预设"""
        current_name = self.prompt_presets_combo.currentText()
        if not current_name:
            return
        
        from ui.preset_dialog import PresetDialog
        presets = config.get_prompt_presets()
        dlg = PresetDialog(self, 
                          name=current_name,
                          content=presets[current_name]['content'],
                          notes=presets[current_name].get('notes', ''))
        if dlg.exec_():
            new_name, content, notes = dlg.get_data()
            config.update_prompt_preset(current_name, new_name, content, notes)
            self.load_prompt_presets()

    def del_prompt_preset(self):
        """删除当前预设"""
        name = self.prompt_presets_combo.currentText()
        if not name:
            return
        
        reply = QMessageBox.question(self, '确认删除', 
                                    f'确定要删除预设 "{name}" 吗？',
                                    QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            config.remove_prompt_preset(name)
            self.load_prompt_presets()