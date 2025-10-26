from PyQt5.QtCore import QObject, pyqtSignal
import cv2

class TranslationSignals(QObject):
    show_translation = pyqtSignal(str, str, str, str, int, int, int, int, tuple)
    overlay_text = pyqtSignal(str, int, int, int, int)
    update_history = pyqtSignal()
    show_error = pyqtSignal(str, str)
    show_ai_study = pyqtSignal()
    # Fire-and-forget signal to open a quick learning game (uses app thread)
    show_game = pyqtSignal()

# OpenCV constants
WINDOW_NORMAL = cv2.WINDOW_NORMAL
EVENT_MOUSEMOVE = cv2.EVENT_MOUSEMOVE
EVENT_LBUTTONDOWN = cv2.EVENT_LBUTTONDOWN
EVENT_LBUTTONUP = cv2.EVENT_LBUTTONUP
FONT_HERSHEY_SIMPLEX = cv2.FONT_HERSHEY_SIMPLEX
COLOR_BGR2GRAY = cv2.COLOR_BGR2GRAY
COLOR_RGB2BGR = cv2.COLOR_RGB2BGR
ADAPTIVE_THRESH_GAUSSIAN_C = cv2.ADAPTIVE_THRESH_GAUSSIAN_C
THRESH_BINARY = cv2.THRESH_BINARY 
