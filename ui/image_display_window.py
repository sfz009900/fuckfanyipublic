"""
Image display window UI component.
"""
import os
import time
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import Qt, QPropertyAnimation, QPoint, QSize, QEasingCurve
import numpy as np
from PyQt5.QtWidgets import QApplication
from config_manager import config

class ImageDisplayWindow(QMainWindow):
    def __init__(self, pil_image=None, title="Image Display", parent=None,
                 animation_enabled=True, animation_type='slide', animation_duration=300):
        super().__init__(parent)
        
        self.setWindowTitle(title)
        
        # 创建中心部件和布局
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # 创建图像标签
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.image_label)
        
        # 设置图像
        if pil_image:
            self.set_image(pil_image)
        
        # 动画设置
        self.animation_enabled = animation_enabled
        self.animation_type = animation_type
        self.animation_duration = animation_duration
        
        # 初始化动画
        self.show_animation = None
        self.hide_animation = None
        
        # 设置窗口样式
        self.setStyleSheet("""
            QMainWindow {
                background: transparent;
            }
            QWidget {
                background: rgba(0, 0, 0, 0.8);
            }
            QLabel {
                background: transparent;
                border: none;
            }
        """)
        
        # 添加提示文本
        self.tip_label = QLabel("按ESC关闭窗口")
        self.tip_label.setStyleSheet("""
            QLabel {
                color: white;
                background-color: rgba(0, 0, 0, 0.7);
                padding: 5px 10px;
                border-radius: 5px;
                font-size: 12px;
            }
        """)
        self.tip_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.tip_label)
        
        # 如果有父窗口，设置为模态对话框
        if parent:
            self.setWindowModality(Qt.WindowModal)
    
    def set_image(self, pil_image):
        """设置要显示的图像"""
        try:
            # 将PIL图像转换为QPixmap
            if pil_image.mode == "RGBA":
                data = pil_image.tobytes("raw", "RGBA")
                qimage = QImage(data, pil_image.size[0], pil_image.size[1], 
                              QImage.Format_RGBA8888)
            else:
                data = pil_image.convert("RGBA").tobytes("raw", "RGBA")
                qimage = QImage(data, pil_image.size[0], pil_image.size[1], 
                              QImage.Format_RGBA8888)
            
            pixmap = QPixmap.fromImage(qimage)
            
            # 获取屏幕大小
            screen = QApplication.primaryScreen().geometry()
            screen_width = screen.width()
            screen_height = screen.height()
            
            # 调整图像大小以适应屏幕
            scaled_pixmap = pixmap.scaled(
                screen_width,
                screen_height,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            
            # 设置图像
            self.image_label.setPixmap(scaled_pixmap)
            
            # 调整窗口大小
            self.adjustSize()
            
        except Exception as e:
            print(f"设置图像时出错: {e}")
            import traceback
            traceback.print_exc()
    
    def setup_animations(self):
        """设置动画效果"""
        if not self.animation_enabled:
            return
        
        try:
            if self.animation_type == 'slide':
                # 滑动动画
                self.show_animation = QPropertyAnimation(self, b"pos")
                self.show_animation.setDuration(self.animation_duration)
                self.show_animation.setEasingCurve(QEasingCurve.OutCubic)
                
                # 从屏幕顶部滑入
                screen = QApplication.primaryScreen().geometry()
                start_pos = QPoint(0, -screen.height())
                end_pos = QPoint(0, 0)
                
                self.show_animation.setStartValue(start_pos)
                self.show_animation.setEndValue(end_pos)
                
            elif self.animation_type == 'fade':
                # 淡入淡出动画
                self.setWindowOpacity(0)
                
                self.show_animation = QPropertyAnimation(self, b"windowOpacity")
                self.show_animation.setDuration(self.animation_duration)
                self.show_animation.setStartValue(0.0)
                self.show_animation.setEndValue(1.0)
                self.show_animation.setEasingCurve(QEasingCurve.InOutCubic)
                
            elif self.animation_type == 'scale':
                # 缩放动画
                self.show_animation = QPropertyAnimation(self, b"size")
                self.show_animation.setDuration(self.animation_duration)
                self.show_animation.setEasingCurve(QEasingCurve.OutBack)
                
                screen = QApplication.primaryScreen().geometry()
                start_size = QSize(screen.width() // 2, screen.height() // 2)
                end_size = QSize(screen.width(), screen.height())
                
                self.show_animation.setStartValue(start_size)
                self.show_animation.setEndValue(end_size)
                
                # 确保窗口在屏幕中心
                self.move(0, 0)
                
        except Exception as e:
            print(f"设置动画时出错: {e}")
            import traceback
            traceback.print_exc()
    
    def showEvent(self, event):
        """窗口显示事件"""
        try:
            super().showEvent(event)
            self.setup_animations()
            if self.show_animation:
                self.show_animation.start()
        except Exception as e:
            print(f"显示窗口时出错: {e}")
            import traceback
            traceback.print_exc()
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        try:
            if not self.animation_enabled or not self.animation_type:
                super().closeEvent(event)
                return
            
            # 创建关闭动画
            if self.animation_type == 'slide':
                self.hide_animation = QPropertyAnimation(self, b"pos")
                self.hide_animation.setDuration(self.animation_duration)
                self.hide_animation.setEasingCurve(QEasingCurve.InCubic)
                
                screen = QApplication.primaryScreen().geometry()
                start_pos = QPoint(0, 0)
                end_pos = QPoint(0, screen.height())
                
                self.hide_animation.setStartValue(start_pos)
                self.hide_animation.setEndValue(end_pos)
                
            elif self.animation_type == 'fade':
                self.hide_animation = QPropertyAnimation(self, b"windowOpacity")
                self.hide_animation.setDuration(self.animation_duration)
                self.hide_animation.setStartValue(1.0)
                self.hide_animation.setEndValue(0.0)
                self.hide_animation.setEasingCurve(QEasingCurve.InOutCubic)
                
            elif self.animation_type == 'scale':
                self.hide_animation = QPropertyAnimation(self, b"size")
                self.hide_animation.setDuration(self.animation_duration)
                self.hide_animation.setEasingCurve(QEasingCurve.InBack)
                
                screen = QApplication.primaryScreen().geometry()
                start_size = QSize(screen.width(), screen.height())
                end_size = QSize(screen.width() // 2, screen.height() // 2)
                
                self.hide_animation.setStartValue(start_size)
                self.hide_animation.setEndValue(end_size)
            
            # 保存事件引用
            self._close_event = event
            
            # 连接动画完成信号
            self.hide_animation.finished.connect(self._finish_close)
            self.hide_animation.start()
            event.ignore()  # 忽略原始的关闭事件
            
        except Exception as e:
            print(f"关闭窗口时出错: {e}")
            import traceback
            traceback.print_exc()
            super().closeEvent(event)
    
    def _finish_close(self):
        """完成窗口关闭"""
        try:
            if hasattr(self, '_close_event'):
                QMainWindow.closeEvent(self, self._close_event)
                delattr(self, '_close_event')
        except Exception as e:
            print(f"完成窗口关闭时出错: {e}")
            import traceback
            traceback.print_exc()
            self.close()
    
    def keyPressEvent(self, event):
        """处理按键事件"""
        if event.key() == Qt.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)
    
    def moveToScreenCenter(self):
        """将窗口移动到屏幕中心"""
        try:
            screen = QApplication.primaryScreen().geometry()
            center_point = screen.center()
            
            # 获取窗口几何信息
            geometry = self.geometry()
            geometry.moveCenter(center_point)
            
            # 设置新的位置
            self.setGeometry(geometry)
        except Exception as e:
            print(f"移动窗口到屏幕中心时出错: {e}")
            import traceback
            traceback.print_exc()
    
    def reload_settings(self):
        """重新加载设置"""
        try:
            # 从配置中重新加载动画设置
            self.animation_enabled = config.get('ANIMATION_EFFECTS', 'animation_enabled')
            self.animation_type = config.get('ANIMATION_EFFECTS', 'animation_type')
            self.animation_duration = config.get('ANIMATION_EFFECTS', 'animation_duration')
            
            # 重新设置动画
            if hasattr(self, 'show_animation') and self.show_animation:
                self.show_animation.setDuration(self.animation_duration)
            if hasattr(self, 'hide_animation') and self.hide_animation:
                self.hide_animation.setDuration(self.animation_duration)
                
            # 更新窗口样式
            self.setStyleSheet("""
                QMainWindow {
                    background: transparent;
                }
                QWidget {
                    background: rgba(0, 0, 0, 0.8);
                }
                QLabel {
                    background: transparent;
                    border: none;
                }
            """)
            
            # 更新提示文本样式
            self.tip_label.setStyleSheet("""
                QLabel {
                    color: white;
                    background-color: rgba(0, 0, 0, 0.7);
                    padding: 5px 10px;
                    border-radius: 5px;
                    font-size: 12px;
                }
            """)
            
        except Exception as e:
            print(f"重新加载设置时出错: {e}")
            import traceback
            traceback.print_exc()