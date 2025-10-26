"""
Runtime hook: ensure the embedded `paddleocr` package is importable
when it has been copied as a data directory into _MEIPASS.

This is defensive: hiddenimports should include the modules; however,
some PaddleOCR code dynamically resolves files by path and importing
directly from the data mirror avoids edge cases.
"""
import os
import sys


def _add_paddleocr_to_sys_path():
    meipass = getattr(sys, "_MEIPASS", None)
    if not meipass:
        return
    candidate = os.path.join(meipass, "paddleocr")
    # Prepend so it takes precedence if both embedded and system copies exist.
    if os.path.isdir(candidate) and candidate not in sys.path:
        sys.path.insert(0, candidate)


_add_paddleocr_to_sys_path()

