import os
import ast
import configparser
import sys
from typing import Any, Dict, Tuple, List

class ConfigManager:
    def __init__(self):
        self.config = configparser.ConfigParser()
        # 判断是否是打包后的EXE
        if getattr(sys, 'frozen', False):
            # 如果是EXE，使用EXE所在目录
            base_path = os.path.dirname(sys.executable)
        else:
            # 如果是开发环境，使用当前文件所在目录
            base_path = os.path.dirname(os.path.abspath(__file__))
        
        self.config_path = os.path.join(base_path, 'config.ini')
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.config.read_file(f)

    def _parse_value(self, value: str) -> Any:
        """Parse string values from config.ini into appropriate Python types."""
        try:
            # Try to evaluate as a Python literal (for tuples, lists, etc.)
            return ast.literal_eval(value)
        except (ValueError, SyntaxError):
            # If not a Python literal, return as string
            return value

    def get(self, section: str, key: str, fallback: Any = None) -> Any:
        """Get a value from the config file with proper type conversion."""
        try:
            value = self.config.get(section, key)
            return self._parse_value(value)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return fallback

    def save_settings(self, settings: Dict[str, Dict[str, Any]]) -> None:
        """保存设置时保留已有预设"""
        # 先保存传入的设置
        for section, values in settings.items():
            if not self.config.has_section(section):
                self.config.add_section(section)
            for key, value in values.items():
                self.config.set(section, key, str(value))
        
        # 将修改后的配置写入文件（包含预设）
        self._save_to_file()

    # 添加私有保存方法
    def _save_to_file(self):
        with open(self.config_path, 'w', encoding='utf-8') as configfile:
            self.config.write(configfile)

    # 修改预设管理方法，每次操作后立即保存
    def add_prompt_preset(self, name, content, notes=""):
        section = f'PROMPT_PRESET:{name}'
        self.config[section] = {
            'content': content,
            'notes': notes
        }
        self._save_to_file()  # 立即保存

    def update_prompt_preset(self, old_name, new_name, content, notes=""):
        self.remove_prompt_preset(old_name)
        self.add_prompt_preset(new_name, content, notes)

    def remove_prompt_preset(self, name):
        section = f'PROMPT_PRESET:{name}'
        if self.config.has_section(section):
            self.config.remove_section(section)
        self._save_to_file()  # 立即保存

    # Convenience properties for commonly used values
    @property
    def SCREENSHOT_HOTKEY(self) -> str:
        return self.get('HOTKEYS', 'SCREENSHOT_HOTKEY')

    @property
    def SOURCE_LANGUAGE(self) -> str:
        return self.get('OCR_TRANSLATION', 'SOURCE_LANGUAGE')

    @property
    def TARGET_LANGUAGE(self) -> str:
        return self.get('OCR_TRANSLATION', 'TARGET_LANGUAGE')

    @property
    def API_URL(self) -> str:
        return self.get('OCR_TRANSLATION', 'API_URL')

    # OCR settings
    @property
    def OCR_LANGUAGE(self) -> str:
        return self.get('PADDLEOCR', 'OCR_LANGUAGE')

    @property
    def OCR_USE_ANGLE_CLS(self) -> bool:
        return self.get('PADDLEOCR', 'OCR_USE_ANGLE_CLS')

    @property
    def OCR_USE_GPU(self) -> bool:
        return self.get('PADDLEOCR', 'OCR_USE_GPU')

    @property
    def OCR_TIMEOUT(self) -> int:
        return self.get('PADDLEOCR', 'OCR_TIMEOUT')

    @property
    def OCR_ENABLE_MKLDNN(self) -> bool:
        return self.get('PADDLEOCR', 'OCR_ENABLE_MKLDNN')

    @property
    def OCR_SHOW_LOG(self) -> bool:
        return self.get('PADDLEOCR', 'OCR_SHOW_LOG')

    # Image processing settings
    @property
    def ENABLE_PREPROCESSING(self) -> bool:
        return self.get('IMAGE_PROCESSING', 'ENABLE_PREPROCESSING')

    @property
    def DENOISE_STRENGTH(self) -> int:
        return self.get('IMAGE_PROCESSING', 'DENOISE_STRENGTH')

    @property
    def CONTRAST_ALPHA(self) -> float:
        return self.get('IMAGE_PROCESSING', 'CONTRAST_ALPHA')

    @property
    def CONTRAST_BETA(self) -> int:
        return self.get('IMAGE_PROCESSING', 'CONTRAST_BETA')

    @property
    def SHARPEN_KERNEL(self) -> List[List[int]]:
        return self.get('IMAGE_PROCESSING', 'SHARPEN_KERNEL')

    # UI settings
    @property
    def OVERLAY_OPACITY(self) -> int:
        return self.get('UI', 'OVERLAY_OPACITY')

    @property
    def SELECTION_COLOR(self) -> Tuple[int, int, int]:
        return self.get('UI', 'SELECTION_COLOR')

    @property
    def GUIDE_COLOR(self) -> Tuple[int, int, int]:
        return self.get('UI', 'GUIDE_COLOR')

    @property
    def CROSSHAIR_COLOR(self) -> Tuple[int, int, int]:
        return self.get('UI', 'CROSSHAIR_COLOR')

    @property
    def CROSSHAIR_SIZE(self) -> int:
        return self.get('UI', 'CROSSHAIR_SIZE')

    @property
    def CROSSHAIR_THICKNESS(self) -> int:
        return self.get('UI', 'CROSSHAIR_THICKNESS')

    @property
    def FONT_SIZE(self) -> int:
        return self.get('UI', 'FONT_SIZE')

    @property
    def FONT_COLOR(self) -> Tuple[int, int, int]:
        return self.get('UI', 'FONT_COLOR')

    @property
    def BACKGROUND_COLOR(self) -> Tuple[int, int, int]:
        return self.get('UI', 'BACKGROUND_COLOR')

    # Hotkey settings
    @property
    def COPY_KEY(self) -> str:
        return self.get('HOTKEYS', 'COPY_KEY')

    @property
    def CLOSE_KEY(self) -> str:
        return self.get('HOTKEYS', 'CLOSE_KEY')

    # Animation settings
    @property
    def ANIMATION_DURATION(self) -> int:
        return self.get('ANIMATION', 'ANIMATION_DURATION')

    @property
    def SELECTION_BORDER_WIDTH(self) -> int:
        return self.get('ANIMATION', 'SELECTION_BORDER_WIDTH')

    @property
    def SELECTION_BORDER_COLOR(self) -> Tuple[int, int, int]:
        return self.get('ANIMATION', 'SELECTION_BORDER_COLOR')

    @property
    def SELECTION_FILL_COLOR(self) -> Tuple[int, int, int, int]:
        return self.get('ANIMATION', 'SELECTION_FILL_COLOR')

    @property
    def GUIDE_FONT_SIZE(self) -> float:
        return self.get('ANIMATION', 'GUIDE_FONT_SIZE')

    @property
    def GUIDE_FONT_THICKNESS(self) -> int:
        return self.get('ANIMATION', 'GUIDE_FONT_THICKNESS')

    @property
    def GUIDE_BG_OPACITY(self) -> float:
        return self.get('ANIMATION', 'GUIDE_BG_OPACITY')

    # Magnifier settings
    @property
    def MAGNIFIER_SIZE(self) -> int:
        return self.get('MAGNIFIER', 'MAGNIFIER_SIZE')

    @property
    def MAGNIFIER_SCALE(self) -> float:
        return self.get('MAGNIFIER', 'MAGNIFIER_SCALE')

    # Overlay settings
    @property
    def OVERLAY_BG_COLOR(self) -> Tuple[int, int, int, int]:
        return self.get('OVERLAY', 'OVERLAY_BG_COLOR', (0, 0, 0, 180))

    @property
    def OVERLAY_TEXT_COLOR(self) -> Tuple[int, int, int, int]:
        return self.get('OVERLAY', 'OVERLAY_TEXT_COLOR', (255, 255, 255, 255))

    @property
    def OVERLAY_FONT_SIZE(self) -> int:
        return self.get('OVERLAY', 'OVERLAY_FONT_SIZE', 14)

    @property
    def OVERLAY_PADDING(self) -> int:
        return self.get('OVERLAY', 'OVERLAY_PADDING', 10)

    @property
    def OVERLAY_LINE_SPACING(self) -> int:
        return self.get('OVERLAY', 'OVERLAY_LINE_SPACING', 2)

    @property
    def OVERLAY_MIN_FONT_SIZE(self) -> int:
        return self.get('OVERLAY', 'OVERLAY_MIN_FONT_SIZE', 8)

    @property
    def OVERLAY_AUTO_EXPAND(self) -> bool:
        return self.get('OVERLAY', 'OVERLAY_AUTO_EXPAND', True)

    @property
    def OVERLAY_TEXT_ALIGNMENT(self) -> str:
        return self.get('OVERLAY', 'OVERLAY_TEXT_ALIGNMENT', 'left')

    @property
    def OVERLAY_FONT_WEIGHT(self) -> str:
        return self.get('OVERLAY', 'OVERLAY_FONT_WEIGHT', 'normal')

    @property
    def OVERLAY_BORDER_WIDTH(self) -> int:
        return self.get('OVERLAY', 'OVERLAY_BORDER_WIDTH', 1)

    @property
    def OVERLAY_BORDER_COLOR(self) -> Tuple[int, int, int, int]:
        return self.get('OVERLAY', 'OVERLAY_BORDER_COLOR', (255, 165, 0, 200))

    @property
    def OVERLAY_SHADOW_ENABLED(self) -> bool:
        return self.get('OVERLAY', 'OVERLAY_SHADOW_ENABLED', True)

    @property
    def OVERLAY_SHADOW_COLOR(self) -> Tuple[int, int, int, int]:
        return self.get('OVERLAY', 'OVERLAY_SHADOW_COLOR', (0, 0, 0, 100))

    @property
    def OVERLAY_SHADOW_OFFSET(self) -> Tuple[int, int]:
        return self.get('OVERLAY', 'OVERLAY_SHADOW_OFFSET', (1, 1))

    @property
    def OVERLAY_TEXT_STROKE_WIDTH(self) -> int:
        return self.get('OVERLAY', 'OVERLAY_TEXT_STROKE_WIDTH', 1)

    @property
    def OVERLAY_TEXT_STROKE_COLOR(self) -> Tuple[int, int, int, int]:
        return self.get('OVERLAY', 'OVERLAY_TEXT_STROKE_COLOR', (0, 0, 0, 255))

    @property
    def OVERLAY_TEXT_GRADIENT_ENABLED(self) -> bool:
        return self.get('OVERLAY', 'OVERLAY_TEXT_GRADIENT_ENABLED', False)

    @property
    def OVERLAY_TEXT_GRADIENT_COLORS(self) -> List[Tuple[int, int, int, int]]:
        return self.get('OVERLAY', 'OVERLAY_TEXT_GRADIENT_COLORS', [(255,255,255,255), (200,200,200,255)])

    @property
    def OVERLAY_BLUR_ENABLED(self) -> bool:
        return self.get('OVERLAY', 'OVERLAY_BLUR_ENABLED', False)

    @property
    def OVERLAY_BLUR_RADIUS(self) -> int:
        return self.get('OVERLAY', 'OVERLAY_BLUR_RADIUS', 10)

    @property
    def OVERLAY_BG_GRADIENT_ENABLED(self) -> bool:
        return self.get('OVERLAY', 'OVERLAY_BG_GRADIENT_ENABLED', False)

    @property
    def OVERLAY_BG_GRADIENT_COLORS(self) -> List[Tuple[int, int, int, int]]:
        return self.get('OVERLAY', 'OVERLAY_BG_GRADIENT_COLORS', [(0,0,0,180), (20,20,20,180)])

    @property
    def OVERLAY_FADE_ENABLED(self) -> bool:
        return self.get('OVERLAY', 'OVERLAY_FADE_ENABLED', True)

    @property
    def OVERLAY_FADE_DURATION(self) -> int:
        return self.get('OVERLAY', 'OVERLAY_FADE_DURATION', 300)

    @property
    def OVERLAY_ANIMATION_ENABLED(self) -> bool:
        return self.get('OVERLAY', 'OVERLAY_ANIMATION_ENABLED', True)

    @property
    def OVERLAY_ANIMATION_TYPE(self) -> str:
        return self.get('OVERLAY', 'OVERLAY_ANIMATION_TYPE', 'slide')

    @property
    def OVERLAY_ANIMATION_DURATION(self) -> int:
        return self.get('OVERLAY', 'OVERLAY_ANIMATION_DURATION', 300)

    @property
    def OVERLAY_CORNER_RADIUS(self) -> int:
        return self.get('VISUAL_STYLE', 'OVERLAY_CORNER_RADIUS', 10)

    @property
    def OVERLAY_TEXT_SPACING(self) -> float:
        return self.get('VISUAL_STYLE', 'OVERLAY_TEXT_SPACING', 1.2)

    @property
    def OVERLAY_TEXT_SHADOW_ENABLED(self) -> bool:
        return self.get('VISUAL_STYLE', 'OVERLAY_TEXT_SHADOW_ENABLED', True)

    @property
    def OVERLAY_TEXT_SHADOW_COLOR(self) -> Tuple[int, int, int, int]:
        return self.get('VISUAL_STYLE', 'OVERLAY_TEXT_SHADOW_COLOR', (0, 0, 0, 100))

    @property
    def OVERLAY_TEXT_SHADOW_OFFSET(self) -> Tuple[int, int]:
        return self.get('VISUAL_STYLE', 'OVERLAY_TEXT_SHADOW_OFFSET', (1, 1))

    @property
    def OVERLAY_TEXT_SHADOW_BLUR(self) -> int:
        return self.get('VISUAL_STYLE', 'OVERLAY_TEXT_SHADOW_BLUR', 2)

    def get_prompt_presets(self):
        presets = {}
        for section in self.config.sections():
            if section.startswith('PROMPT_PRESET:'):
                preset_name = section.split(':', 1)[1]
                presets[preset_name] = {
                    'content': self.config.get(section, 'content'),
                    'notes': self.config.get(section, 'notes', fallback='')
                }
        return presets

    def has_section(self, section):
        """检查配置是否有指定的section"""
        return self.config.has_section(section)
    
    def add_section(self, section):
        """添加新的section"""
        if not self.has_section(section):
            self.config.add_section(section)
    
    def set(self, section, option, value):
        """设置配置项"""
        if not self.has_section(section):
            self.add_section(section)
        self.config.set(section, option, str(value))
    
    def save(self):
        """保存配置到文件"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            self.config.write(f)

# Create a global instance
config = ConfigManager() 