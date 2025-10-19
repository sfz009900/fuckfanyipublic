"""
Main entry point for the OCR translator application.
"""
import sys
import os
import platform
from PIL import ImageGrab
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction, QStyle
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QTimer

from config_manager import config
from core.ocr_translator import OCRTranslator

def register_hotkey(hotkeys, translator):
    """Register global hotkeys using Windows RegisterHotKey."""
    try:
        # 1 = screenshot, 2 = AI 学习
        hotkeys.register(1, config.SCREENSHOT_HOTKEY, translator.start_translation)
        ai_hotkey = config.get('HOTKEYS', 'AI_STUDY_HOTKEY', 'ctrl+alt+x')
        hotkeys.register(2, ai_hotkey, translator.show_ai_study)
        print(f"已注册全局热键: {config.SCREENSHOT_HOTKEY}，AI学习: {ai_hotkey}")
    except Exception as e:
        print(f"注册系统热键失败: {e}")


def check_hotkey(_translator):
    """使用RegisterHotKey后无需定时自检。"""
    return


def main():
    """
    Main function to start the OCR translator application.
    """
    # 使用系统级热键，无需 keyboard 句柄
    # 创建 QApplication 实例
    app = QApplication(sys.argv)
    
    # 设置应用程序信息
    app.setApplicationName("OCR Translator")
    app.setQuitOnLastWindowClosed(False)  # 关闭窗口时不退出应用
    
    # 创建 OCRTranslator 实例
    translator = OCRTranslator()
    
    # 提前定义变量，供后续闭包引用
    hotkeys = None

    # 创建系统托盘图标
    tray_icon = QSystemTrayIcon()
    
    # 使用自定义图标
    if getattr(sys, 'frozen', False):
        # 如果是EXE，使用EXE所在目录
        base_path = os.path.dirname(sys.executable)
    else:
        # 如果是开发环境，使用当前文件所在目录
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    icon_path = os.path.join(base_path, "assets", "icon.png")
    if os.path.exists(icon_path):
        icon = QIcon(icon_path)
        tray_icon.setIcon(icon)
    else:
        # 如果自定义图标不存在，使用内置图标
        print(f"警告: 找不到图标文件 {icon_path}，使用内置图标")
        # QStyle 已导入，防止之前的未定义错误
        icon = app.style().standardIcon(QStyle.SP_ComputerIcon)
        tray_icon.setIcon(icon)
    
    tray_icon.setToolTip("OCR Translator")
    
    # 创建托盘菜单
    menu = QMenu()
    
    # 添加翻译动作
    translate_action = QAction("开始翻译")
    translate_action.triggered.connect(translator.start_translation)
    menu.addAction(translate_action)
    
    # 添加查看历史记录动作
    history_action = QAction("查看历史记录")
    history_action.triggered.connect(translator.show_history)
    menu.addAction(history_action)

    # 添加AI学习动作
    ai_study_action = QAction("AI学习")
    ai_study_action.triggered.connect(translator.show_ai_study)
    menu.addAction(ai_study_action)

    # 添加设置动作
    settings_action = QAction("设置")
    settings_action.triggered.connect(translator.show_settings)
    menu.addAction(settings_action)
    
    # 添加重新注册热键动作
    reregister_action = QAction("重新注册热键")
    reregister_action.triggered.connect(lambda: register_hotkey(hotkeys, translator))
    menu.addAction(reregister_action)
    
    # 添加分隔线
    menu.addSeparator()
    
    # 添加关于动作
    about_action = QAction("关于")
    about_action.triggered.connect(translator.show_about)
    menu.addAction(about_action)
    
    # 添加分隔线
    menu.addSeparator()
    
    # 添加退出动作
    exit_action = QAction("退出")
    def _quit():
        try:
            if hotkeys is not None:
                hotkeys.unregister_all()
        finally:
            app.quit()
    exit_action.triggered.connect(_quit)
    menu.addAction(exit_action)
    
    # 设置托盘菜单
    tray_icon.setContextMenu(menu)
    tray_icon.show()
    
    # 注册全局热键（仅Windows支持）
    if platform.system() != 'Windows':
        print('警告: 全局热键仅在Windows上受支持，当前平台无法注册。')
        hotkeys = None
    else:
        from utils.global_hotkeys import GlobalHotkeys
        hotkeys = GlobalHotkeys(app)
        register_hotkey(hotkeys, translator)
    
    # 创建定时器检查热键状态
    # 使用 RegisterHotKey 后无需定时检查
    # 保留变量名避免引用错误
    hotkey_timer = None
    
    # 显示启动消息
    tray_icon.showMessage("OCR Translator", 
                         f"OCR翻译器已启动，按 {config.SCREENSHOT_HOTKEY} 开始截图翻译",
                         QSystemTrayIcon.Information, 3000)
    print(f"OCR翻译器已启动，按 {config.SCREENSHOT_HOTKEY} 开始截图翻译")
    
    # 运行应用程序
    sys.exit(app.exec_())


if __name__ == "__main__":
    main() 
