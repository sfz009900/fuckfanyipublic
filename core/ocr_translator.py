import keyboard
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import sys
import os
import time
import win32gui
import win32con
import win32api
from PyQt5.QtWidgets import (QApplication, QMessageBox)
from PyQt5.QtCore import QTimer
from PyQt5.QtCore import Qt
import threading

from .signals import TranslationSignals, WINDOW_NORMAL, EVENT_MOUSEMOVE, EVENT_LBUTTONDOWN, EVENT_LBUTTONUP
from .image_processor import ImageProcessor
from .ocr_handler import OCRHandler
from .translator import Translator
from .history_manager import HistoryManager
from ui.image_display_window import ImageDisplayWindow
from ui.translation_window import TranslationWindow
from ui.history_dialog import HistoryDialog
from ui.settings_dialog import SettingsDialog
from ui.about_dialog import AboutDialog
from ui.ai_study_dialog import AIStudyDialog
from config_manager import config

class OCRTranslator:
    def __init__(self):
        # Initialize components
        self.image_processor = ImageProcessor()
        self.ocr_handler = OCRHandler()
        self.translator = Translator()
        
        # 根据运行环境确定基础路径
        if getattr(sys, 'frozen', False):
            # 如果是EXE，使用EXE所在目录
            base_path = os.path.dirname(sys.executable)
        else:
            # 如果是开发环境，使用当前文件所在目录的上级目录
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        self.history_manager = HistoryManager(
            os.path.join(base_path, "history", "translation_history.json")
        )
        
        # Initialize state variables
        self.selection_start = None
        self.selection_end = None
        self.is_selecting = False
        self.screenshot = None
        self.original_screenshot = None
        self.selected_region = None
        self.translated_text = None
        self.window_name = "Screenshot Translator"
        self.translation_window_name = "Translation Result"
        self.last_selection_coords = None
        
        # UI settings from config
        self.overlay_opacity = config.get('UI', 'overlay_opacity')
        self.selection_color = config.get('UI', 'selection_color')
        self.guide_color = config.get('UI', 'guide_color')
        self.crosshair_color = config.get('UI', 'crosshair_color')
        self.crosshair_size = config.get('UI', 'crosshair_size')
        self.crosshair_thickness = config.get('UI', 'crosshair_thickness')
        self.font_size = config.get('UI', 'font_size')
        self.font_color = config.get('UI', 'font_color')
        self.background_color = config.get('UI', 'background_color')
        
        # Hotkeys
        self.copy_key = config.get('HOTKEYS', 'copy_key')
        self.close_key = config.get('HOTKEYS', 'close_key')
        
        # Animation settings
        self.animation_duration = config.get('ANIMATION', 'animation_duration')
        self.selection_border_width = config.get('ANIMATION', 'selection_border_width')
        self.selection_border_color = config.get('ANIMATION', 'selection_border_color')
        self.selection_fill_color = config.get('ANIMATION', 'selection_fill_color')
        self.guide_font_size = config.get('ANIMATION', 'guide_font_size')
        self.guide_font_thickness = config.get('ANIMATION', 'guide_font_thickness')
        self.guide_bg_opacity = config.get('ANIMATION', 'guide_bg_opacity')
        
        # Magnifier settings
        self.magnifier_size = config.get('MAGNIFIER', 'magnifier_size')
        self.magnifier_scale = config.get('MAGNIFIER', 'magnifier_scale')
        
        # Overlay settings
        self.overlay_bg_color = config.get('OVERLAY', 'overlay_bg_color')
        self.overlay_text_color = config.get('OVERLAY', 'overlay_text_color')
        self.overlay_font_size = config.get('OVERLAY', 'overlay_font_size')
        self.overlay_padding = config.get('OVERLAY', 'overlay_padding')
        self.overlay_line_spacing = config.get('OVERLAY', 'overlay_line_spacing')
        self.overlay_min_font_size = config.get('OVERLAY', 'overlay_min_font_size')
        self.overlay_auto_expand = config.get('OVERLAY', 'overlay_auto_expand')
        self.overlay_text_alignment = config.get('OVERLAY', 'overlay_text_alignment')
        self.overlay_font_weight = config.get('OVERLAY', 'overlay_font_weight')
        self.overlay_border_width = config.get('OVERLAY', 'overlay_border_width')
        self.overlay_border_color = config.get('OVERLAY', 'overlay_border_color')
        self.overlay_shadow_enabled = config.get('OVERLAY', 'overlay_shadow_enabled')
        self.overlay_shadow_color = config.get('OVERLAY', 'overlay_shadow_color')
        self.overlay_shadow_offset = config.get('OVERLAY', 'overlay_shadow_offset')
        # Smart cover options
        self.overlay_mode = config.get('OVERLAY', 'overlay_mode', 'inpaint')  # 'inpaint' or 'box'
        self.overlay_auto_text_color = config.get('OVERLAY', 'overlay_auto_text_color', True)
        self.overlay_inpaint_radius = config.get('OVERLAY', 'overlay_inpaint_radius', 3)
        self.overlay_inpaint_dilate = config.get('OVERLAY', 'overlay_inpaint_dilate', 1)
        
        # Text effects settings
        self.text_stroke_width = config.get('TEXT_EFFECTS', 'text_stroke_width')
        self.text_gradient_enabled = config.get('TEXT_EFFECTS', 'text_gradient_enabled')
        self.blur_enabled = config.get('TEXT_EFFECTS', 'blur_enabled')
        self.blur_radius = config.get('TEXT_EFFECTS', 'blur_radius')
        self.bg_gradient_enabled = config.get('TEXT_EFFECTS', 'bg_gradient_enabled')
        
        # Animation effects settings
        self.animation_enabled = config.get('ANIMATION_EFFECTS', 'animation_enabled')
        self.animation_type = config.get('ANIMATION_EFFECTS', 'animation_type')
        self.animation_duration = config.get('ANIMATION_EFFECTS', 'animation_duration')
        
        # 确保有一个QApplication实例
        if not QApplication.instance():
            self.app = QApplication(sys.argv)
        else:
            self.app = QApplication.instance()
        
        # 创建信号对象
        self.signals = TranslationSignals()
        self.signals.show_translation.connect(self._show_translation_window)
        self.signals.overlay_text.connect(self.overlay_text_to_image)
        self.signals.update_history.connect(self.history_manager.save_history)
        self.signals.show_error.connect(self.show_error_message)
        self.signals.show_ai_study.connect(self._open_ai_study)
        
        self.translation_window = None
        self.image_display_window = None
        # 单例 AI学习 窗口引用
        self.ai_study_dialog = None
    
    def register_hotkey(self):
        """Register the hotkey to start the translation process"""
        keyboard.add_hotkey(config.SCREENSHOT_HOTKEY, self.start_translation)
        print(f"OCR Translator is running. Press {config.SCREENSHOT_HOTKEY} to capture and translate.")
        
        # 创建一个永久运行的事件循环
        while True:
            self.app.processEvents()  # 处理Qt事件
            time.sleep(0.1)  # 避免CPU占用过高
    
    def start_translation(self):
        """Start the translation process by taking a screenshot"""
        try:
            print("Taking screenshot...")
            self.screenshot, self.original_screenshot = self.image_processor.take_screenshot()
            self.select_region()
        except Exception as e:
            print(f"翻译过程中发生错误: {e}")
            cv2.destroyAllWindows()
            print("已重置应用程序状态，可以重新开始翻译。")
    
    def select_region(self):
        """Allow the user to select a region on the screenshot"""
        try:
            # 创建无边框全屏窗口
            cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL | cv2.WINDOW_FREERATIO)
            cv2.setWindowProperty(self.window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
            
            # 获取虚拟屏幕尺寸（多显示器支持）
            try:
                vs_left = win32api.GetSystemMetrics(76)   # SM_XVIRTUALSCREEN
                vs_top = win32api.GetSystemMetrics(77)    # SM_YVIRTUALSCREEN
                screen_width = win32api.GetSystemMetrics(78)  # SM_CXVIRTUALSCREEN
                screen_height = win32api.GetSystemMetrics(79) # SM_CYVIRTUALSCREEN
            except Exception:
                screen_width = win32api.GetSystemMetrics(0)
                screen_height = win32api.GetSystemMetrics(1)
            
            cv2.resizeWindow(self.window_name, screen_width, screen_height)
            
            # 设置窗口置顶
            hwnd = win32gui.FindWindow(None, self.window_name)
            if hwnd:
                try:
                    # 使用虚拟屏幕坐标确保覆盖所有显示器
                    win32gui.SetWindowPos(
                        hwnd, win32con.HWND_TOPMOST,
                        vs_left if 'vs_left' in locals() else 0,
                        vs_top if 'vs_top' in locals() else 0,
                        screen_width, screen_height,
                        win32con.SWP_SHOWWINDOW
                    )
                except Exception:
                    win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, screen_width, screen_height, win32con.SWP_SHOWWINDOW)
            
            cv2.setMouseCallback(self.window_name, self.mouse_callback)
            
            # Create a semi-transparent overlay
            overlay = self.screenshot.copy()
            alpha = 0.3
            cv2.rectangle(overlay, (0, 0), (overlay.shape[1], overlay.shape[0]), (0, 0, 0), -1)
            cv2.addWeighted(overlay, alpha, self.screenshot, 1 - alpha, 0, self.screenshot)
            
            self.display_img = self.screenshot.copy()
            cv2.imshow(self.window_name, self.display_img)
            
            while True:
                if win32gui.FindWindow(None, self.window_name) == 0:
                    print("截图选择窗口已关闭")
                    return
                
                key = cv2.waitKey(10)
                
                if key == 27:  # ESC
                    if win32gui.FindWindow(None, self.window_name) != 0:
                        try:
                            cv2.destroyWindow(self.window_name)
                        except:
                            cv2.destroyAllWindows()
                    return
        except Exception as e:
            print(f"选择区域时出现错误: {e}")
            cv2.destroyAllWindows()
    
    def mouse_callback(self, event, x, y, flags, param):
        """Mouse callback for region selection"""
        temp_img = self.display_img.copy()
        
        if event == EVENT_LBUTTONDOWN:
            self.selection_start = (x, y)
            self.is_selecting = True
            
            cv2.line(temp_img, 
                    (max(0, x - self.crosshair_size), y), 
                    (min(temp_img.shape[1], x + self.crosshair_size), y), 
                    self.crosshair_color, self.crosshair_thickness)
            cv2.line(temp_img, 
                    (x, max(0, y - self.crosshair_size)), 
                    (x, min(temp_img.shape[0], y + self.crosshair_size)), 
                    self.crosshair_color, self.crosshair_thickness)
            
            cv2.circle(temp_img, self.selection_start, 3, self.selection_color, -1)
            cv2.imshow(self.window_name, temp_img)
        
        elif event == EVENT_MOUSEMOVE and self.is_selecting:
            cv2.rectangle(temp_img, self.selection_start, (x, y), self.selection_color, 2)
            cv2.imshow(self.window_name, temp_img)
        
        elif event == EVENT_LBUTTONUP:
            self.selection_end = (x, y)
            self.is_selecting = False
            
            x1 = min(self.selection_start[0], self.selection_end[0])
            y1 = min(self.selection_start[1], self.selection_end[1])
            x2 = max(self.selection_start[0], self.selection_end[0])
            y2 = max(self.selection_start[1], self.selection_end[1])
            
            highlight_color = (0, 200, 255)
            cv2.rectangle(self.screenshot, (x1-2, y1-2), (x2+2, y2+2), highlight_color, 2)
            cv2.rectangle(self.screenshot, (x1, y1), (x2, y2), self.selection_color, 2)
            
            mask = np.zeros((self.screenshot.shape[0], self.screenshot.shape[1]), dtype=np.uint8)
            cv2.rectangle(mask, (x1, y1), (x2, y2), 255, -1)
            
            highlight = np.zeros_like(self.screenshot)
            highlight[mask > 0] = [255, 255, 0]
            
            pulse_img = self.screenshot.copy()
            alpha = 0.2
            cv2.addWeighted(pulse_img, 1, highlight, alpha, 0, pulse_img)
            
            cv2.imshow(self.window_name, pulse_img)
            cv2.waitKey(1)
            
            self.process_selected_region()
        
        elif not self.is_selecting:
            cv2.imshow(self.window_name, temp_img)
    
    def process_selected_region(self):
        """Process the selected region for OCR and translation in background"""
        try:
            # 销毁截图窗口
            if win32gui.FindWindow(None, self.window_name) != 0:
                try:
                    cv2.destroyWindow(self.window_name)
                except:
                    cv2.destroyAllWindows()
            
            if self.selection_start and self.selection_end:
                # 获取选中区域坐标
                x1 = min(self.selection_start[0], self.selection_end[0])
                y1 = min(self.selection_start[1], self.selection_end[1])
                x2 = max(self.selection_start[0], self.selection_end[0])
                y2 = max(self.selection_start[1], self.selection_end[1])
                
                # 保存最后一次选择的坐标
                self.last_selection_coords = (x1, y1, x2, y2)
                
                # 在后台线程中执行OCR和翻译，避免阻塞UI
                def worker():
                    source_text, result = self.ocr_and_translate(x1, y1, x2, y2)
                    if source_text is None:
                        self.signals.show_error.emit("OCR识别失败", result)
                        return
                    if isinstance(result, str):
                        self.signals.show_error.emit("翻译失败", result)
                        # 显示原文
                        self.display_translation(source_text, source_text, "unknown", "unknown", x1, y1, x2, y2)
                    else:
                        self.display_translation(
                            result['translated_text'], 
                            source_text, 
                            result['source_lang'], 
                            result['target_lang'], 
                            x1, y1, x2, y2
                        )
                threading.Thread(target=worker, daemon=True).start()
        except Exception as e:
            print(f"处理选中区域时出错: {e}")
            cv2.destroyAllWindows()
    
    def ocr_and_translate(self, x1, y1, x2, y2):
        """Perform OCR and translation on the selected region"""
        try:
            # 确保坐标为整数
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
            
            # 从原始截图（numpy数组）中裁剪区域
            # 确保original_screenshot是numpy数组格式
            if hasattr(self, 'original_screenshot'):
                if isinstance(self.original_screenshot, Image.Image):
                    # 如果是PIL Image，转为numpy数组
                    img_array = np.array(self.original_screenshot)
                    region = img_array[y1:y2, x1:x2]
                else:
                    # 已经是numpy数组
                    region = self.original_screenshot[y1:y2, x1:x2]
            else:
                print("错误: 没有找到原始截图")
                return None, "截图过程出错，请重试"
            
            # 调用OCR处理器识别文本
            source_text = self.ocr_handler.perform_ocr(region)
            
            if not source_text:
                # OCR失败时返回错误消息
                return None, "OCR识别失败，未能识别出文本。请尝试选择更清晰的文本区域。"
            
            # 调用翻译器进行翻译
            translate_result = self.translator.translate(source_text)
            
            if translate_result is None:
                # 翻译失败时返回原文本和错误消息
                return source_text, "翻译失败，请检查网络连接或API设置。"
            
            # 翻译成功，保存到历史记录
            self.history_manager.add_translation(
                source_text, 
                translate_result['translated_text'],
                translate_result['source_lang'],
                translate_result['target_lang']
            )
            
            # 返回OCR识别的文本和翻译结果
            return source_text, translate_result
        except Exception as e:
            print(f"OCR和翻译过程中出错: {str(e)}")
            import traceback
            traceback.print_exc()  # 打印详细错误信息
            return None, f"处理失败: {str(e)}"
    
    def show_error_message(self, title, message):
        """Display error message to user"""
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()
    
    def display_translation(self, translated_text, source_text, source_lang, target_lang, x1, y1, x2, y2):
        """Display the translation result in the UI"""
        try:
            # 打印日志
            print("===== OCR结果 =====")
            print(source_text)
            print("===== 翻译结果 =====")
            print(translated_text)
            
            # 计算显示位置 - 窗口应该显示在选定区域下方
            screen_width = win32api.GetSystemMetrics(0)
            screen_height = win32api.GetSystemMetrics(1)
            
            # 计算原始选择区域的宽度和高度
            sel_width = x2 - x1
            sel_height = y2 - y1
            
            # 保存原始坐标，用于后续覆盖操作
            original_coords = (x1, y1, sel_width, sel_height)
            
            window_width = min(max(sel_width, 400), screen_width - 100)  # 最小宽度400，不超过屏幕
            window_pos_x = max(0, x1)  # 窗口左上角x坐标
            window_pos_y = min(y2 + 10, screen_height - 100)  # 窗口左上角y坐标，如果太靠下则调整
            
            # 发送信号更新界面
            self.signals.show_translation.emit(
                translated_text,  # 翻译结果
                source_text,      # 原文
                source_lang,      # 源语言
                target_lang,      # 目标语言
                window_pos_x,     # 窗口x坐标
                window_pos_y,     # 窗口y坐标
                window_width,     # 窗口宽度
                min(screen_height - window_pos_y - 50, 600),  # 窗口高度
                original_coords   # 原始选择区域坐标
            )
        except Exception as e:
            print(f"显示翻译结果时出错: {e}")
    
    def _show_translation_window(self, translated_text, source_text, source_lang, target_lang, pos_x, pos_y, width, height, original_coords):
        """在主线程中创建和显示翻译窗口"""
        try:
            # 打印输入到翻译窗口的文本格式
            print("===== 原文段落格式 =====")
            for i, p in enumerate(source_text.split("\n\n")):
                print(f"原文段落{i+1}: {p}")
            
            print("===== 译文段落格式 =====")
            for i, p in enumerate(translated_text.split("\n\n")):
                print(f"译文段落{i+1}: {p}")
            
            if self.translation_window:
                self.translation_window.close()
                self.translation_window = None
            
            self.translation_window = TranslationWindow(
                translated_text, source_text, source_lang, target_lang,
                pos_x, pos_y, width, height, original_coords
            )
            self.translation_window.parent = lambda: self
            self.translation_window.show()
            
            # 如果设置对话框存在且有效，连接其信号到翻译窗口
            if hasattr(self, 'settings_dialog') and self.settings_dialog and not self.settings_dialog.isHidden():
                try:
                    self.settings_dialog.settings_changed.connect(self.translation_window.update_settings)
                except (RuntimeError, AttributeError):
                    # 如果对话框已被删除或无效，忽略错误
                    pass
        except Exception as e:
            print(f"显示翻译窗口时出错: {e}")
            import traceback
            traceback.print_exc()
    
    def overlay_text_to_image(self, text, x, y, width, height):
        """将译文覆盖到原始截图位置
        
        Args:
            text (str): 要覆盖的文本
            x (int): 覆盖区域左上角x坐标
            y (int): 覆盖区域左上角y坐标
            width (int): 覆盖区域宽度
            height (int): 覆盖区域高度
            
        Returns:
            bool: 操作是否成功
        """
        try:
            if not self._validate_overlay_params(text, x, y, width, height):
                return False
            
            # 确保original_screenshot是PIL Image对象
            if isinstance(self.original_screenshot, np.ndarray):
                # 如果是numpy数组，转换为PIL Image
                pil_img = Image.fromarray(cv2.cvtColor(self.original_screenshot, cv2.COLOR_BGR2RGB))
            elif isinstance(self.original_screenshot, Image.Image):
                # 已经是PIL Image
                pil_img = self.original_screenshot.copy()
            else:
                print(f"错误: 不支持的图像类型 {type(self.original_screenshot)}")
                return False
            
            draw = ImageDraw.Draw(pil_img)
            
            # 获取屏幕尺寸，用于限制覆盖区域的大小
            screen_width = win32api.GetSystemMetrics(0)
            screen_height = win32api.GetSystemMetrics(1)
            
            # 计算覆盖区域
            x1, y1 = x, y
            
            # 不再自动调整宽度，使用原始选定的宽度
            # 只进行必要的屏幕边界检查
            if x + width > screen_width:
                width = screen_width - x - 10  # 保留10像素边距
            
            x2, y2 = x + width, y + height
            
            # 加载并设置字体
            fonts = self._get_font()
            if not fonts:
                return False
            
            # 打印调试信息
            print(f"覆盖文本区域: x1={x1}, y1={y1}, x2={x2}, y2={y2}")
            print(f"覆盖文本内容: {text}")
            
            # 计算文本布局
            lines, total_height = self._calculate_text_layout(text, fonts['chinese'], width - 2 * self.overlay_padding)
            
            if not lines:
                return False
            
            # 打印详细的调试信息
            print(f"原始边框区域: x1={x1}, y1={y1}, x2={x2}, y2={y2}, 尺寸={width}x{height}")
            print(f"内边距: {self.overlay_padding}px")
            print(f"文本渲染区域: x1={x1 + self.overlay_padding}, y1={y1 + self.overlay_padding}, "
                  f"宽度={width - 2 * self.overlay_padding}, 高度={height - 2 * self.overlay_padding}")
            
            # 如果需要自动扩展高度并且用户明确开启了此功能
            if self.overlay_auto_expand:
                # 计算需要的高度，并调整y2
                required_height = total_height + 2 * self.overlay_padding
                if required_height > height:
                    print(f"自动扩展高度: {height} -> {required_height}")
                    new_y2 = y1 + required_height
                    # 确保不超出屏幕底部
                    if new_y2 > screen_height:
                        new_y2 = screen_height - 10  # 保留10像素边距
                    y2 = new_y2
                    height = y2 - y1
            
            # 根据覆盖模式处理背景
            if str(self.overlay_mode).lower() == 'inpaint':
                try:
                    pil_img = self._smart_cover_background(pil_img, x1, y1, x2, y2)
                    draw = ImageDraw.Draw(pil_img)
                    print("已使用智能覆盖模式(inpaint)清理原文背景")
                except Exception as _e:
                    print(f"智能覆盖失败，回退到box模式: {_e}")
                    self._draw_background_and_border(draw, x1, y1, x2, y2)
            else:
                # 传统盒子模式
                self._draw_background_and_border(draw, x1, y1, x2, y2)
            
            # 计算带内边距的起始位置
            render_x1 = x1 + self.overlay_padding
            render_y1 = y1 + self.overlay_padding
            
            # 如果不允许自动扩展，则尝试自适应缩小字体以适配高度
            if not self.overlay_auto_expand:
                target_height = max(0, height - 2 * self.overlay_padding)
                fit_size = self._fit_font_to_box(text, width - 2 * self.overlay_padding, target_height, fonts)
                if fit_size and fit_size != self.overlay_font_size:
                    print(f"自适应缩放字体: {self.overlay_font_size} -> {fit_size}")
                    fonts = self._get_font_with_size(fit_size)
                    lines, total_height = self._calculate_text_layout(text, fonts['chinese'], width - 2 * self.overlay_padding)

            # 自动选择文本颜色以保持对比度（仅在智能覆盖模式下默认启用）
            prev_color = None
            if str(self.overlay_mode).lower() == 'inpaint' and self.overlay_auto_text_color:
                try:
                    # 取清理后的ROI估算背景亮度
                    roi = np.array(pil_img)[y1:y2, x1:x2]
                    auto_color = self._pick_auto_text_color(roi)
                    prev_color = self.overlay_text_color
                    self.overlay_text_color = auto_color
                    print(f"自动选择文本颜色: {prev_color} -> {auto_color}")
                except Exception as _:
                    prev_color = None

            # 渲染文本
            self._render_text(draw, lines, fonts, render_x1, render_y1, width - 2 * self.overlay_padding, height - 2 * self.overlay_padding)

            # 恢复原始文本颜色，避免影响后续操作
            if prev_color is not None:
                self.overlay_text_color = prev_color
            
            # 如果需要转回OpenCV格式，可以在这里转换
            display_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            
            # 显示结果
            self._show_result_window(display_img)
            
            return True
            
        except Exception as e:
            print(f"覆盖原文到图像时出错: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _validate_overlay_params(self, text, x, y, width, height):
        """验证覆盖参数的有效性"""
        if self.original_screenshot is None:
            print("错误：没有可用的原始截图")
            return False
        
        if not text or not text.strip():
            print("错误：文本内容为空")
            return False
            
        if width <= 0 or height <= 0:
            print("错误：覆盖区域尺寸无效")
            return False
            
        return True
    
    def _get_font(self):
        """获取字体对象，使用字体回退机制支持中文和彩色表情符号

        兼容可选的size参数: 如果self._temp_font_size存在则优先使用
        """
        try:
            # 根据运行环境确定基础路径
            if getattr(sys, 'frozen', False):
                # 如果是EXE，使用EXE所在目录
                base_path = os.path.dirname(sys.executable)
            else:
                # 如果是开发环境，使用当前文件所在目录的上级目录
                base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            # 获取fonts目录的绝对路径
            fonts_dir = os.path.join(base_path, "fonts")
            
            if not os.path.exists(fonts_dir):
                os.makedirs(fonts_dir)
                print(f"创建字体目录: {fonts_dir}")
            
            # 加载中文字体
            chinese_font_paths = [
                os.path.join(fonts_dir, "msyh.ttc"),  # 微软雅黑
                os.path.join(fonts_dir, "simhei.ttf"),  # 黑体
                os.path.join(fonts_dir, "simsun.ttc"),  # 宋体
            ]
            
            chinese_font = None
            for path in chinese_font_paths:
                try:
                    if os.path.exists(path):
                        size = getattr(self, '_temp_font_size', self.overlay_font_size)
                        chinese_font = ImageFont.truetype(path, size)
                        print(f"成功加载中文字体: {path}")
                        break
                except Exception:
                    continue
            
            if chinese_font is None:
                print("警告：无法加载中文字体，将使用默认字体")
                chinese_font = ImageFont.load_default()
            
            # 加载彩色表情符号字体
            emoji_font_paths = [
                os.path.join(fonts_dir, "seguiemj.ttf"),  # Segoe UI Emoji
                os.path.join(fonts_dir, "seguisym.ttf"),  # Segoe UI Symbol
                os.path.join(fonts_dir, "segoeui.ttf"),   # Segoe UI
            ]
            
            emoji_font = None
            for path in emoji_font_paths:
                try:
                    if os.path.exists(path):
                        size = getattr(self, '_temp_font_size', self.overlay_font_size)
                        emoji_font = ImageFont.truetype(path, size)
                        print(f"成功加载emoji字体: {path}")
                        break
                except Exception:
                    continue
            
            if emoji_font is None:
                print("警告：无法加载emoji字体，将使用中文字体作为后备")
                emoji_font = chinese_font
            
            return {
                'chinese': chinese_font,
                'emoji': emoji_font
            }
            
        except Exception as e:
            print(f"加载字体失败: {e}，尝试使用默认字体")
            try:
                return {'default': ImageFont.load_default()}
            except Exception as e:
                print(f"加载默认字体也失败: {e}")
                return None

    def _get_font_with_size(self, size: int):
        """按指定字号加载字体，返回{'chinese','emoji'}"""
        self._temp_font_size = size
        try:
            fonts = self._get_font()
        finally:
            if hasattr(self, '_temp_font_size'):
                delattr(self, '_temp_font_size')
        return fonts
    
    def _calculate_text_layout(self, text, font, width):
        """计算文本布局"""
        try:
            max_width = width  # 不需要减去内边距，因为调用时已经传入了有效宽度
            lines = []
            total_height = 0  # 初始高度设为0，不预留顶部空间
            
            # 设置行间距，长行被强制换行时，使用段落间距
            paragraph_spacing = 0.8  # 段落间距
            inline_spacing = 0.4  # 段落内行间距
            
            print(f"计算文本布局 - 可用宽度: {max_width}px, 段落间距: {paragraph_spacing}, 段落内行间距: {inline_spacing}")
            
            # 如果max_width太小，设置一个最小值
            if max_width < 200:
                max_width = 200
                print(f"警告: 宽度太小，已调整为最小宽度: {max_width}px")
            
            # 检查文本是否包含多个段落
            if "\n\n" in text:
                # 分割段落处理
                paragraphs = text.split("\n\n")
                all_lines = []
                
                # 计算每个段落的行
                for i, paragraph in enumerate(paragraphs):
                    # 检测是否为中文文本
                    is_chinese = any('\u4e00' <= char <= '\u9fff' for char in paragraph)
                    paragraph_lines = []
                    current_line = ""
                    
                    if is_chinese:
                        # 中文文本按字符换行
                        for char in paragraph:
                            test_line = current_line + char
                            bbox = font.getbbox(test_line)
                            if bbox[2] <= max_width:
                                current_line = test_line
                            else:
                                if current_line:
                                    # 对于长行强制换行的情况，使用段落间距而不是行内间距
                                    paragraph_lines.append((current_line, False))
                                    # 使用段落间距，防止行重叠
                                    total_height += bbox[3] * paragraph_spacing
                                current_line = char
                    else:
                        # 英文文本按单词换行
                        words = paragraph.split()
                        for word in words:
                            # 如果当前行为空，但单词本身就超出最大宽度，则需要强制切分单词
                            if (not current_line and font.getbbox(word)[2] > max_width) or len(word) > 30:
                                # 逐字符添加，直到达到最大宽度
                                temp_word = ""
                                for char in word:
                                    test_word = temp_word + char
                                    if font.getbbox(test_word)[2] <= max_width:
                                        temp_word = test_word
                                    else:
                                        if temp_word:
                                            # 对于长单词强制拆分的情况，使用段落间距
                                            paragraph_lines.append((temp_word, False))
                                            bbox = font.getbbox(temp_word)
                                            # 使用段落间距，防止行重叠
                                            total_height += bbox[3] * paragraph_spacing
                                        temp_word = char
                                
                                # 处理剩余部分
                                if temp_word:
                                    current_line = temp_word
                                continue
                                
                            # 常规单词处理
                            test_line = current_line + (" " if current_line else "") + word
                            bbox = font.getbbox(test_line)
                            if bbox[2] <= max_width:
                                current_line = test_line
                            else:
                                if current_line:
                                    # 正常换行情况，使用段落间距
                                    paragraph_lines.append((current_line, False))
                                    # 使用段落间距，防止行重叠
                                    total_height += bbox[3] * paragraph_spacing
                                current_line = word
                    
                    # 添加最后一行
                    if current_line:
                        # 添加一个标记(True)表示这是段落的结束行
                        paragraph_lines.append((current_line, True))
                        bbox = font.getbbox(current_line)
                        # 使用较大的段落间距
                        total_height += bbox[3] * paragraph_spacing
                    
                    # 将当前段落的行添加到所有行
                    if paragraph_lines:
                        all_lines.extend(paragraph_lines)
                        # 如果不是最后一个段落，添加空行作为段落分隔
                        if i < len(paragraphs) - 1:
                            all_lines.append(("", True))
                            total_height += font.getbbox("A")[3] * paragraph_spacing
                
                # 设置结果
                lines = all_lines
            else:
                # 检测是否为中文文本
                is_chinese = any('\u4e00' <= char <= '\u9fff' for char in text)
                
                current_line = ""  # 添加缺失的变量
                
                if is_chinese:
                    # 中文文本按字符换行
                    for char in text:
                        test_line = current_line + char
                        bbox = font.getbbox(test_line)
                        if bbox[2] <= max_width:
                            current_line = test_line
                        else:
                            if current_line:
                                # 对于长行强制换行的情况，使用段落间距
                                lines.append((current_line, False))
                                # 使用段落间距，防止行重叠
                                total_height += bbox[3] * paragraph_spacing
                            current_line = char
                else:
                    # 英文文本按单词换行，特殊处理超长单词
                    words = text.split()
                    for word in words:
                        # 特殊处理：如果当前行为空但词语本身就超长，或者单词太长
                        if (not current_line and font.getbbox(word)[2] > max_width) or len(word) > 30:
                            # 逐字符添加，直到达到最大宽度
                            temp_word = ""
                            for char in word:
                                test_word = temp_word + char
                                if font.getbbox(test_word)[2] <= max_width:
                                    temp_word = test_word
                                else:
                                    if temp_word:
                                        # 对于长单词强制拆分的情况，使用段落间距
                                        lines.append((temp_word, False))
                                        bbox = font.getbbox(temp_word)
                                        # 使用段落间距，防止行重叠
                                        total_height += bbox[3] * paragraph_spacing
                                    temp_word = char
                            
                            # 处理剩余部分
                            if temp_word:
                                current_line = temp_word
                            continue
                            
                        # 常规单词处理
                        test_line = current_line + (" " if current_line else "") + word
                        bbox = font.getbbox(test_line)
                        if bbox[2] <= max_width:
                            current_line = test_line
                        else:
                            if current_line:
                                # 正常换行，使用段落间距
                                lines.append((current_line, False))
                                # 使用段落间距，防止行重叠
                                total_height += bbox[3] * paragraph_spacing
                            current_line = word
                
                # 添加最后一行
                if current_line:
                    # 最后一行是段落结束
                    lines.append((current_line, True))
                    bbox = font.getbbox(current_line)
                    total_height += bbox[3] * paragraph_spacing
            
            # 增加额外空间确保行间不重叠
            extra_space = total_height * 0.1  # 增加10%的总高度作为缓冲
            total_height += extra_space
            
            # 在方法结束前打印行数和总高度信息
            print(f"文本布局计算完成 - 共{len(lines)}行, 总高度: {total_height}px")
            
            return lines, total_height
            
        except Exception as e:
            print(f"计算文本布局时出错: {e}")
            import traceback
            traceback.print_exc()
            return None, 0
    
    def _adjust_overlay_height(self, y1, total_height):
        """调整覆盖区域高度"""
        new_height = total_height + 2 * self.overlay_padding
        y2 = y1 + new_height
        print(f"自动扩展覆盖区域高度至: {new_height}")
        return y2, new_height
    
    def _draw_background_and_border(self, draw, x1, y1, x2, y2):
        """绘制背景和边框，支持渐变和模糊效果"""
        try:
            # 减少内边距，使文本更好地填充整个区域
            print(f"绘制背景区域: x1={x1}, y1={y1}, x2={x2}, y2={y2}, 尺寸={x2-x1}x{y2-y1}")
            
            # 计算圆角半径 - 使用较小的值避免空间浪费
            rounded_radius = min(5, config.get('OVERLAY', 'OVERLAY_CORNER_RADIUS', 5))
            
            if config.get('OVERLAY', 'OVERLAY_BLUR_ENABLED', False):
                # 创建模糊效果的背景
                blur_radius = config.get('OVERLAY', 'OVERLAY_BLUR_RADIUS', 10)
                background = Image.new('RGBA', (x2-x1, y2-y1), (0,0,0,0))
                background = background.filter(ImageFilter.GaussianBlur(blur_radius))
                draw.bitmap((x1, y1), background)
            
            if config.get('OVERLAY', 'OVERLAY_BG_GRADIENT_ENABLED', False):
                # 创建渐变背景
                gradient_colors = config.get('OVERLAY', 'OVERLAY_BG_GRADIENT_COLORS',
                                       [(0,0,0,180), (20,20,20,180)])
                self._draw_gradient_background(draw, x1, y1, x2, y2, gradient_colors)
            else:
                # 绘制普通背景
                draw.rounded_rectangle(
                    [x1, y1, x2, y2],
                    radius=rounded_radius,
                    fill=self.overlay_bg_color
                )
            
            # 绘制阴影
            if config.get('OVERLAY', 'OVERLAY_SHADOW_ENABLED', True):
                shadow_color = config.get('OVERLAY', 'OVERLAY_SHADOW_COLOR', (0, 0, 0, 100))
                shadow_blur = config.get('OVERLAY', 'OVERLAY_SHADOW_BLUR', 5)
                shadow_offset = config.get('OVERLAY', 'OVERLAY_SHADOW_OFFSET', (2, 2))
                
                shadow = Image.new('RGBA', (x2-x1, y2-y1), (0,0,0,0))
                shadow_draw = ImageDraw.Draw(shadow)
                shadow_draw.rounded_rectangle(
                    [0, 0, x2-x1, y2-y1],
                    radius=rounded_radius,
                    fill=shadow_color
                )
                shadow = shadow.filter(ImageFilter.GaussianBlur(shadow_blur))
                draw.bitmap((x1 + shadow_offset[0], y1 + shadow_offset[1]), shadow)
            
            # 绘制边框
            border_width = config.get('OVERLAY', 'OVERLAY_BORDER_WIDTH', 2)
            border_color = config.get('OVERLAY', 'OVERLAY_BORDER_COLOR', (255, 165, 0, 200))
            
            if border_width > 0:
                for i in range(border_width):
                    draw.rounded_rectangle(
                        [x1+i, y1+i, x2-i, y2-i],
                        radius=max(1, rounded_radius-i),
                        outline=border_color
                    )
        except Exception as e:
            print(f"绘制背景和边框时出错: {e}")
    
    def _draw_gradient_background(self, draw, x1, y1, x2, y2, colors):
        """绘制渐变背景"""
        try:
            width = x2 - x1
            height = y2 - y1
            gradient = Image.new('RGBA', (width, height), (0,0,0,0))
            gradient_draw = ImageDraw.Draw(gradient)
            
            for y in range(height):
                # 计算当前位置的颜色
                ratio = y / height
                r = int(colors[0][0] + (colors[1][0] - colors[0][0]) * ratio)
                g = int(colors[0][1] + (colors[1][1] - colors[0][1]) * ratio)
                b = int(colors[0][2] + (colors[1][2] - colors[0][2]) * ratio)
                a = int(colors[0][3] + (colors[1][3] - colors[0][3]) * ratio)
                gradient_draw.line([(0, y), (width, y)], fill=(r,g,b,a))
            
            draw.bitmap((x1, y1), gradient)
        except Exception as e:
            print(f"绘制渐变背景时出错: {e}")
    
    def _render_text(self, draw, lines, fonts, x1, y1, width, height):
        """渲染文本，支持渐变、描边和阴影效果"""
        try:
            # 顶部边距设为0，直接从顶部开始
            alignment = config.get('OVERLAY', 'OVERLAY_TEXT_ALIGNMENT', 'left')
            
            # 设置与_calculate_text_layout方法一致的行间距因子
            paragraph_spacing = 0.8  # 段落间距
            inline_spacing = 0.4  # 段落内行间距
            
            print(f"设置段落间距={paragraph_spacing}, 段落内行间距={inline_spacing}, 顶部边距=0px")
            
            # 明确初始化current_y变量，从传入的y1位置开始（已经包含内边距）
            current_y = y1
            print(f"明确初始化文本起始位置: current_y={current_y} (包含内边距)")
            
            # 文本阴影与描边设置（智能覆盖时默认关闭以更贴近原图风格）
            if str(self.overlay_mode).lower() == 'inpaint':
                shadow_enabled = False
                stroke_width = 0
                shadow_color = (0, 0, 0, 0)
                shadow_offset = (0, 0)
                shadow_blur = 0
                stroke_color = (0, 0, 0, 0)
            else:
                shadow_enabled = config.get('OVERLAY', 'OVERLAY_TEXT_SHADOW_ENABLED', True)
                shadow_color = config.get('OVERLAY', 'OVERLAY_TEXT_SHADOW_COLOR', (0, 0, 0, 100))
                shadow_offset = config.get('OVERLAY', 'OVERLAY_TEXT_SHADOW_OFFSET', (1, 1))
                shadow_blur = config.get('OVERLAY', 'OVERLAY_TEXT_SHADOW_BLUR', 2)
                # 文本描边设置
                stroke_width = config.get('OVERLAY', 'OVERLAY_TEXT_STROKE_WIDTH', 1)
                stroke_color = config.get('OVERLAY', 'OVERLAY_TEXT_STROKE_COLOR', (0, 0, 0, 255))
            
            # 文本渐变设置
            gradient_enabled = config.get('OVERLAY', 'OVERLAY_TEXT_GRADIENT_ENABLED', False)
            gradient_colors = config.get('OVERLAY', 'OVERLAY_TEXT_GRADIENT_COLORS',
                                   [(255,255,255,255), (200,200,200,255)])
            
            # 字间距设置 - 减小默认字间距，使文本更紧凑
            char_spacing = config.get('OVERLAY', 'OVERLAY_CHAR_SPACING', -1)  # 默认值为-1，表示字符间距略微紧凑
            
            # 预先计算每行的高度
            line_heights = []
            for line_info in lines:
                # 解析行和段落标记
                if isinstance(line_info, tuple) and len(line_info) == 2:
                    line, _ = line_info
                else:
                    # 兼容旧格式
                    line = line_info
                
                # 如果是空行，使用基本字体高度
                if not line:
                    line_heights.append(fonts['chinese'].getbbox("A")[3])
                    continue
                    
                # 计算行高度
                char_heights = [fonts['emoji' if self._is_emoji(char) else 'chinese'].getbbox(char)[3] 
                               for char in line]
                line_heights.append(max(char_heights) if char_heights else fonts['chinese'].getbbox("A")[3])
            
            # 渲染每一行
            for i, (line_info, line_height) in enumerate(zip(lines, line_heights)):
                # 解析行和段落标记
                if isinstance(line_info, tuple) and len(line_info) == 2:
                    line, is_paragraph_end = line_info
                else:
                    # 兼容旧格式
                    line = line_info
                    is_paragraph_end = True
                
                # 如果是空行，只增加行高
                if not line:
                    if i > 0:  # 不是第一行时才增加间距
                        current_y += line_height * paragraph_spacing
                    continue
                
                # 计算行宽度用于对齐
                total_width = sum(fonts['emoji' if self._is_emoji(char) else 'chinese'].getbbox(char)[2] 
                                for char in line)
                # 考虑字间距调整
                total_width += char_spacing * (len(line) - 1)
                
                # 根据对齐方式计算起始x坐标
                if alignment == 'center':
                    x_start = x1 + (width - total_width) // 2
                elif alignment == 'right':
                    x_start = x1 + width - total_width - 5  # 使用较小的右边距(5px)
                else:  # left
                    x_start = x1 + 5  # 使用较小的左边距(5px)
                
                x_offset = x_start
                
                # 渲染每个字符
                for j, char in enumerate(line):
                    is_emoji = self._is_emoji(char)
                    font = fonts['emoji' if is_emoji else 'chinese']
                    bbox = font.getbbox(char)
                    char_width = bbox[2]
                    
                    # 渲染文本阴影
                    if shadow_enabled and not is_emoji:
                        shadow_img = Image.new('RGBA', (char_width*2, line_height*2), (0,0,0,0))
                        shadow_draw = ImageDraw.Draw(shadow_img)
                        shadow_draw.text(
                            (char_width//2, line_height//2),
                            char,
                            font=font,
                            fill=shadow_color
                        )
                        shadow_img = shadow_img.filter(ImageFilter.GaussianBlur(shadow_blur))
                        draw.bitmap(
                            (x_offset + shadow_offset[0], current_y + shadow_offset[1]),
                            shadow_img
                        )
                    
                    # 渲染文本描边
                    if stroke_width > 0 and not is_emoji:
                        for dx, dy in [(dx,dy) for dx in range(-stroke_width,stroke_width+1) 
                                     for dy in range(-stroke_width,stroke_width+1)]:
                            if dx != 0 or dy != 0:
                                draw.text(
                                    (x_offset + dx, current_y + dy),
                                    char,
                                    font=font,
                                    fill=stroke_color
                                )
                    
                    # 渲染文本
                    if is_emoji:
                        draw.text(
                            (x_offset, current_y),
                            char,
                            font=font,
                            embedded_color=True
                        )
                    else:
                        if gradient_enabled:
                            # 创建渐变文本
                            ratio = (current_y - y1) / height
                            r = int(gradient_colors[0][0] + (gradient_colors[1][0] - gradient_colors[0][0]) * ratio)
                            g = int(gradient_colors[0][1] + (gradient_colors[1][1] - gradient_colors[0][1]) * ratio)
                            b = int(gradient_colors[0][2] + (gradient_colors[1][2] - gradient_colors[0][2]) * ratio)
                            a = int(gradient_colors[0][3] + (gradient_colors[1][3] - gradient_colors[0][3]) * ratio)
                            text_color = (r,g,b,a)
                        else:
                            text_color = self.overlay_text_color
                        
                        draw.text(
                            (x_offset, current_y),
                            char,
                            font=font,
                            fill=text_color
                        )
                    
                    # 更新x位置到下一个字符，考虑字间距调整
                    x_offset += char_width
                    if j < len(line) - 1:  # 不是行的最后一个字符
                        x_offset += char_spacing  # 应用字间距调整
                
                # 更新y位置到下一行
                if i < len(lines) - 1:  # 不是最后一行
                    # 对所有换行都使用段落间距，避免行重叠
                    current_y += line_height * paragraph_spacing
                    print(f"行{i+1}应用段落间距: {paragraph_spacing}")
                
        except Exception as e:
            print(f"渲染文本时出错: {e}")
            import traceback
            traceback.print_exc()
            
    def _build_text_mask(self, roi_bgr: np.ndarray) -> np.ndarray:
        """构建文本掩码：结合顶帽/黑帽和边缘来增强文字笔画，输出二值掩码"""
        try:
            gray = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2GRAY)
            # 平滑以降低噪声，但保留笔画
            gray_blur = cv2.bilateralFilter(gray, 5, 30, 30)

            # 顶帽(亮字) + 黑帽(暗字)突出文字
            k = max(1, int(self.overlay_inpaint_dilate))
            ksize = 2 * k + 1
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(3, ksize), max(3, ksize)))
            tophat = cv2.morphologyEx(gray_blur, cv2.MORPH_TOPHAT, kernel)
            blackhat = cv2.morphologyEx(gray_blur, cv2.MORPH_BLACKHAT, kernel)
            enhance = cv2.addWeighted(tophat, 0.6, blackhat, 0.6, 0)

            # 梯度/边缘辅助
            grad = cv2.morphologyEx(gray_blur, cv2.MORPH_GRADIENT, kernel)
            edges = cv2.Canny(gray_blur, 60, 180)
            enhance = cv2.addWeighted(enhance, 0.8, grad, 0.2, 0)

            # Otsu二值化获取笔画
            _, mask1 = cv2.threshold(enhance, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            mask = cv2.bitwise_or(mask1, edges)

            # 形态学操作扩大笔画覆盖
            kernel2 = cv2.getStructuringElement(cv2.MORPH_RECT, (max(3, ksize), max(3, ksize)))
            mask = cv2.dilate(mask, kernel2, iterations=1)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel2, iterations=1)
            return mask
        except Exception as e:
            print(f"构建文本掩码失败: {e}")
            return np.zeros(roi_bgr.shape[:2], dtype=np.uint8)

    def _smart_cover_background(self, pil_img: Image.Image, x1: int, y1: int, x2: int, y2: int) -> Image.Image:
        """对选区进行inpaint，尽量抹除原文，仅保留背景"""
        img_bgr = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        roi = img_bgr[y1:y2, x1:x2].copy()
        if roi.size == 0:
            return pil_img
        # 1) 首次inpaint：按文本掩码进行
        mask = self._build_text_mask(roi)
        radius = int(self.overlay_inpaint_radius) if self.overlay_inpaint_radius else 3
        try:
            inpainted = cv2.inpaint(roi, mask, radius, cv2.INPAINT_TELEA)
        except Exception:
            inpainted = cv2.inpaint(roi, mask, radius, cv2.INPAINT_NS)

        # 2) 评估残留：若仍有明显笔画，使用更激进的清理方案
        remain = self._build_text_mask(inpainted)
        orig_count = max(1, int(cv2.countNonZero(mask)))
        remain_count = int(cv2.countNonZero(remain))
        area = max(1, roi.shape[0] * roi.shape[1])
        # 若残留占原掩码30%以上或占ROI面积超过1.5%，认定清理不充分
        if remain_count / orig_count > 0.3 or remain_count / area > 0.015:
            try:
                # 方案A：对ROI做较强中值模糊，彻底抹除细节
                k = 21 if min(roi.shape[0], roi.shape[1]) > 80 else 11
                blurred = cv2.medianBlur(roi, k)
                # 为避免边界突兀，与边界做轻微融合
                alpha = 0.85
                inpainted = cv2.addWeighted(inpainted, 1 - alpha, blurred, alpha, 0)
                print("首次修复残留较多，已使用强力模糊回退方案清理背景")
            except Exception as _:
                pass

        img_bgr[y1:y2, x1:x2] = inpainted
        return Image.fromarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))

    def _pick_auto_text_color(self, roi_bgr: np.ndarray):
        """根据背景亮度自动选择黑/白文字，提高可读性"""
        if roi_bgr.size == 0:
            return self.overlay_text_color
        gray = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2GRAY)
        # 使用中位数亮度更稳健
        brightness = float(np.median(gray))
        # 阈值在[0,255]，中性设为140略偏亮
        if brightness < 140:
            return (255, 255, 255, 255)  # 背景偏暗，用白字
        else:
            return (0, 0, 0, 255)        # 背景偏亮，用黑字

    def _fit_font_to_box(self, text: str, box_w: int, box_h: int, fonts_current) -> int:
        """尝试减小字体直至排版高度不超过box_h，返回合适字号或原字号"""
        try:
            size = getattr(self, '_temp_font_size', None) or self.overlay_font_size
            min_size = max(8, int(self.overlay_min_font_size))
            while size >= min_size:
                f = self._get_font_with_size(size)
                lines, total_h = self._calculate_text_layout(text, f['chinese'], box_w)
                if total_h <= box_h:
                    return size
                size -= 1
            return min_size
        except Exception as _:
            return self.overlay_font_size
    def _is_emoji(self, char):
        """判断字符是否为emoji"""
        try:
            return any([
                # 基本emoji范围
                '\U0001F300' <= char <= '\U0001F9FF',
                # 补充符号和象形文字
                '\U0001F000' <= char <= '\U0001F02F',
                # 装饰符号
                '\U0001F1E6' <= char <= '\U0001F1FF',
                # 其他额外的emoji范围
                '\U0001F900' <= char <= '\U0001F9FF',
                '\U0001FA70' <= char <= '\U0001FAFF'
            ])
        except Exception:
            return False
    
    def _show_result_window(self, img):
        """显示结果窗口，支持动画效果
        
        Args:
            img: 可以是PIL Image对象或OpenCV图像(numpy.ndarray)
        """
        def show_custom_window():
            try:
                if self.translation_window:
                    self.translation_window.close()
                    self.translation_window = None
                
                # 确保图像是PIL格式，如果是numpy数组（OpenCV格式）则转换
                pil_image = None
                if isinstance(img, np.ndarray):
                    # 转换BGR到RGB
                    if img.shape[2] == 3:  # 如果是3通道图像
                        rgb_image = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                        pil_image = Image.fromarray(rgb_image)
                    else:
                        # 其他情况直接转换
                        pil_image = Image.fromarray(img)
                elif isinstance(img, Image.Image):
                    pil_image = img
                else:
                    print(f"不支持的图像类型: {type(img)}")
                    return
                
                # 获取活动窗口作为父窗口
                parent = QApplication.activeWindow()
                
                self.image_display_window = ImageDisplayWindow(
                    pil_image=pil_image,
                    title="覆盖后的图像",
                    parent=None,  # 设置为None以支持全屏
                    animation_enabled=False,  # 禁用动画效果
                    animation_duration=0
                )
                
                # 设置窗口标志为无边框全屏
                self.image_display_window.setWindowFlags(
                    Qt.FramelessWindowHint | 
                    Qt.WindowStaysOnTopHint | 
                    Qt.Tool
                )
                self.image_display_window.setAttribute(Qt.WA_TranslucentBackground)
                
                # 获取主屏幕尺寸
                screen = QApplication.primaryScreen().geometry()
                
                # 设置窗口大小为全屏
                self.image_display_window.setGeometry(screen)
                
                # 显示窗口
                self.image_display_window.show()
                self.image_display_window.activateWindow()
                self.image_display_window.raise_()
                
            except Exception as e:
                print(f"显示结果窗口时出错: {e}")
                import traceback
                traceback.print_exc()
        
        QTimer.singleShot(0, show_custom_window)
    
    def show_history(self):
        """显示历史记录对话框"""
        dialog = HistoryDialog(self.history_manager.get_history())
        dialog.exec_()
        self.history_manager.save_history()

    def show_about(self):
        """显示关于对话框"""
        dialog = AboutDialog()
        dialog.exec_()

    def show_ai_study(self):
        """触发显示 AI学习 窗口（与热键绑定，无初始文本）。"""
        try:
            # 为兼容原有信号使用，仍通过信号切入主线程
            self.signals.show_ai_study.emit()
        except Exception as e:
            print(f"派发AI学习窗口信号失败: {e}")

    def show_ai_study_with_text(self, initial_text: str, auto_start: bool = True):
        """从UI线程或其他线程请求显示 AI学习 窗口，并填充文本。"""
        try:
            # 使用Qt计时器在事件循环中执行，避免线程问题
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(0, lambda: self._open_ai_study_internal(initial_text, auto_start))
        except Exception as e:
            print(f"显示AI学习窗口(带文本)时出错: {e}")

    def _open_ai_study(self):
        """兼容原有无参信号的槽函数。"""
        self._open_ai_study_internal()

    def _on_ai_study_destroyed(self, *_):
        try:
            self.ai_study_dialog = None
        except Exception:
            pass

    def _open_ai_study_internal(self, initial_text: str = None, auto_start: bool = False):
        from PyQt5.QtWidgets import QApplication
        try:
            print("打开AI学习窗口…")
            # 如果已有实例且仍然有效，则复用
            if self.ai_study_dialog is not None:
                try:
                    # 可能已被Qt删除，调用属性以测试有效性
                    _ = self.ai_study_dialog.windowTitle()
                    if initial_text:
                        try:
                            self.ai_study_dialog.start_with_text(initial_text, auto_start)
                        except Exception as _:
                            pass
                    # 还原最小化并置顶激活
                    try:
                        if self.ai_study_dialog.isMinimized():
                            self.ai_study_dialog.showNormal()
                        else:
                            self.ai_study_dialog.show()
                        self.ai_study_dialog.raise_()
                        self.ai_study_dialog.activateWindow()
                    except Exception:
                        self.ai_study_dialog.show()
                    return
                except RuntimeError:
                    # C++对象已被删除，置空等待重建
                    self.ai_study_dialog = None

            # 创建新实例
            parent_window = QApplication.activeWindow()
            self.ai_study_dialog = AIStudyDialog(parent_window, initial_text=initial_text or None, auto_start=auto_start)
            try:
                self.ai_study_dialog.destroyed.connect(self._on_ai_study_destroyed)
            except Exception:
                pass
            # 使用 show 而不是 exec_，以便实现单例复用
            self.ai_study_dialog.show()
            self.ai_study_dialog.raise_()
            self.ai_study_dialog.activateWindow()
        except Exception as e:
            print(f"显示AI学习窗口时出错: {e}")
            import traceback
            traceback.print_exc()

    def reload_settings(self):
        """重新加载设置"""
        # UI settings
        self.overlay_opacity = config.get('UI', 'overlay_opacity')
        self.selection_color = config.get('UI', 'selection_color')
        self.guide_color = config.get('UI', 'guide_color')
        self.crosshair_color = config.get('UI', 'crosshair_color')
        self.crosshair_size = config.get('UI', 'crosshair_size')
        self.crosshair_thickness = config.get('UI', 'crosshair_thickness')
        self.font_size = config.get('UI', 'font_size')
        self.font_color = config.get('UI', 'font_color')
        self.background_color = config.get('UI', 'background_color')
        
        # Hotkeys
        self.copy_key = config.get('HOTKEYS', 'copy_key')
        self.close_key = config.get('HOTKEYS', 'close_key')
        
        # Animation settings
        self.animation_duration = config.get('ANIMATION', 'animation_duration')
        self.selection_border_width = config.get('ANIMATION', 'selection_border_width')
        self.selection_border_color = config.get('ANIMATION', 'selection_border_color')
        self.selection_fill_color = config.get('ANIMATION', 'selection_fill_color')
        self.guide_font_size = config.get('ANIMATION', 'guide_font_size')
        self.guide_font_thickness = config.get('ANIMATION', 'guide_font_thickness')
        self.guide_bg_opacity = config.get('ANIMATION', 'guide_bg_opacity')
        
        # Magnifier settings
        self.magnifier_size = config.get('MAGNIFIER', 'magnifier_size')
        self.magnifier_scale = config.get('MAGNIFIER', 'magnifier_scale')
        
        # Overlay settings
        self.overlay_bg_color = config.get('OVERLAY', 'overlay_bg_color')
        self.overlay_text_color = config.get('OVERLAY', 'overlay_text_color')
        self.overlay_font_size = config.get('OVERLAY', 'overlay_font_size')
        self.overlay_padding = config.get('OVERLAY', 'overlay_padding')
        self.overlay_line_spacing = config.get('OVERLAY', 'overlay_line_spacing')
        self.overlay_min_font_size = config.get('OVERLAY', 'overlay_min_font_size')
        self.overlay_auto_expand = config.get('OVERLAY', 'overlay_auto_expand')
        self.overlay_text_alignment = config.get('OVERLAY', 'overlay_text_alignment')
        self.overlay_font_weight = config.get('OVERLAY', 'overlay_font_weight')
        self.overlay_border_width = config.get('OVERLAY', 'overlay_border_width')
        self.overlay_border_color = config.get('OVERLAY', 'overlay_border_color')
        self.overlay_shadow_enabled = config.get('OVERLAY', 'overlay_shadow_enabled')
        self.overlay_shadow_color = config.get('OVERLAY', 'overlay_shadow_color')
        self.overlay_shadow_offset = config.get('OVERLAY', 'overlay_shadow_offset')
        # Smart cover options
        self.overlay_mode = config.get('OVERLAY', 'overlay_mode', self.overlay_mode)
        self.overlay_auto_text_color = config.get('OVERLAY', 'overlay_auto_text_color', self.overlay_auto_text_color)
        self.overlay_inpaint_radius = config.get('OVERLAY', 'overlay_inpaint_radius', self.overlay_inpaint_radius)
        self.overlay_inpaint_dilate = config.get('OVERLAY', 'overlay_inpaint_dilate', self.overlay_inpaint_dilate)
        
        # Text effects settings
        self.text_stroke_width = config.get('TEXT_EFFECTS', 'text_stroke_width')
        self.text_gradient_enabled = config.get('TEXT_EFFECTS', 'text_gradient_enabled')
        self.blur_enabled = config.get('TEXT_EFFECTS', 'blur_enabled')
        self.blur_radius = config.get('TEXT_EFFECTS', 'blur_radius')
        self.bg_gradient_enabled = config.get('TEXT_EFFECTS', 'bg_gradient_enabled')
        
        # Animation effects settings
        self.animation_enabled = config.get('ANIMATION_EFFECTS', 'animation_enabled')
        self.animation_type = config.get('ANIMATION_EFFECTS', 'animation_type')
        self.animation_duration = config.get('ANIMATION_EFFECTS', 'animation_duration')
        
        # 重新加载OCR和翻译设置
        self.ocr_handler.reload_settings()
        self.translator.reload_settings()
        
        # 更新UI组件
        if self.translation_window:
            self.translation_window.update_settings({
                'OVERLAY_FONT_SIZE': self.overlay_font_size,
                'OVERLAY_PADDING': self.overlay_padding,
                'OVERLAY_LINE_SPACING': self.overlay_line_spacing,
                'OVERLAY_TEXT_ALIGNMENT': self.overlay_text_alignment,
                'OVERLAY_FONT_WEIGHT': self.overlay_font_weight
            })
        if self.image_display_window:
            self.image_display_window.reload_settings()

    def show_settings(self):
        """显示设置对话框"""
        try:
            # 如果已经存在设置对话框且仍然有效，则直接显示
            if hasattr(self, 'settings_dialog') and self.settings_dialog and not self.settings_dialog.isHidden():
                self.settings_dialog.activateWindow()
                self.settings_dialog.raise_()
                return
                
            # 使用当前活动窗口作为父窗口
            parent_window = self.app.activeWindow()
            if not parent_window and self.translation_window:
                parent_window = self.translation_window
                
            self.settings_dialog = SettingsDialog(parent_window)
            
            # 如果翻译窗口存在，连接设置变更信号
            if self.translation_window:
                self.settings_dialog.settings_changed.connect(self.translation_window.update_settings)
            
            # 连接设置变更信号到重载设置方法
            self.settings_dialog.settings_changed.connect(self.reload_settings)
            
            # 连接对话框关闭信号
            self.settings_dialog.finished.connect(self._on_settings_dialog_closed)
            
            self.settings_dialog.exec_()
        except Exception as e:
            print(f"显示设置对话框时出错: {e}")
            import traceback
            traceback.print_exc()
            
    def _on_settings_dialog_closed(self, result):
        """处理设置对话框关闭事件"""
        try:
            # 断开所有信号连接
            if self.settings_dialog:
                self.settings_dialog.settings_changed.disconnect()
                self.settings_dialog.finished.disconnect()
                self.settings_dialog = None
        except Exception:
            pass

if __name__ == "__main__":
    translator = OCRTranslator()
    translator.register_hotkey() 
