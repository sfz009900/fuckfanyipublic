"""
Signal classes for the OCR translator application.
"""
from PyQt5.QtCore import QObject, pyqtSignal


class TranslationSignals(QObject):
    """
    Signals for translation events.
    """
    # Signal for showing translation window
    # Parameters: translated_text, source_text, source_lang, target_lang, pos_x, pos_y, width, height, original_coords
    show_translation = pyqtSignal(str, str, str, str, int, int, int, int, tuple)
    
    # Signal for overlaying text on image
    # Parameters: text, x, y, width, height
    overlay_text = pyqtSignal(str, int, int, int, int)
    
    # Signal for updating history list
    update_history = pyqtSignal() 