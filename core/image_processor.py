import cv2
import numpy as np
from PIL import ImageGrab
from .signals import COLOR_RGB2BGR

# Optional fast screenshot backend
try:
    import mss
    MSS_AVAILABLE = True
except Exception:
    MSS_AVAILABLE = False

class ImageProcessor:
    def __init__(self, denoise_strength=10, contrast_alpha=1.3, contrast_beta=0):
        self.denoise_strength = denoise_strength
        self.contrast_alpha = contrast_alpha
        self.contrast_beta = contrast_beta
        self.sharpen_kernel = np.array([[-1,-1,-1], 
                                      [-1, 9,-1], 
                                      [-1,-1,-1]], dtype=np.float32)

    def take_screenshot(self):
        """Take a screenshot of the entire screen"""
        try:
            if MSS_AVAILABLE:
                with mss.mss() as sct:
                    monitor = sct.monitors[0]  # full virtual screen
                    sct_img = sct.grab(monitor)
                    img = np.array(sct_img)  # BGRA
                    screenshot_cv = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            else:
                # 使用PIL的ImageGrab获取屏幕截图
                screenshot = ImageGrab.grab()
                # 将PIL图像转换为numpy数组(OpenCV格式)
                screenshot_cv = cv2.cvtColor(np.array(screenshot), COLOR_RGB2BGR)
            
            print("截图成功")
            return screenshot_cv, screenshot_cv  # 返回两个OpenCV格式的图像
        except Exception as e:
            print(f"截图过程中出错: {e}")
            import traceback
            traceback.print_exc()
            # 创建一个空白图像作为备用
            blank_image = np.zeros((100, 100, 3), dtype=np.uint8)
            return blank_image, blank_image

    def preprocess_image(self, image):
        """Enhance image quality for better OCR results"""
        try:
            # Convert to grayscale if needed
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()
            
            # Apply denoising
            denoised = cv2.fastNlMeansDenoising(gray, None, self.denoise_strength)
            
            # Enhance contrast
            contrasted = cv2.convertScaleAbs(denoised, alpha=self.contrast_alpha, beta=self.contrast_beta)
            
            # Apply sharpening
            sharpened = cv2.filter2D(contrasted, -1, self.sharpen_kernel)
            
            # Binarization using adaptive threshold
            binary = cv2.adaptiveThreshold(sharpened, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                         cv2.THRESH_BINARY, 11, 2)
            
            return binary
        except Exception as e:
            print(f"Image preprocessing failed: {e}")
            return image 
