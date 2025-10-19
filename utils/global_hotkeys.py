import ctypes
from ctypes import wintypes
from typing import Callable, Dict, Tuple

from PyQt5.QtCore import QAbstractNativeEventFilter, QObject


# Windows constants
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
WM_HOTKEY = 0x0312


user32 = ctypes.windll.user32


def _vk_code(key: str) -> int:
    """Convert a key string (e.g., 'A', '1', 'F5', 'ESC') to a virtual-key code."""
    k = key.upper()
    # Single alphanumeric
    if len(k) == 1 and 'A' <= k <= 'Z':
        return ord(k)
    if len(k) == 1 and '0' <= k <= '9':
        return ord(k)

    # Function keys
    if k.startswith('F') and k[1:].isdigit():
        n = int(k[1:])
        if 1 <= n <= 24:
            return 0x70 + (n - 1)  # VK_F1=0x70

    # Common named keys
    mapping = {
        'ESC': 0x1B,
        'ESCAPE': 0x1B,
        'TAB': 0x09,
        'CAPSLOCK': 0x14,
        'SPACE': 0x20,
        'ENTER': 0x0D,
        'RETURN': 0x0D,
        'LEFT': 0x25,
        'UP': 0x26,
        'RIGHT': 0x27,
        'DOWN': 0x28,
        'HOME': 0x24,
        'END': 0x23,
        'PRIOR': 0x21,  # PageUp
        'PAGEUP': 0x21,
        'NEXT': 0x22,   # PageDown
        'PAGEDOWN': 0x22,
        'INSERT': 0x2D,
        'DELETE': 0x2E,
        'BACKSPACE': 0x08,
    }
    if k in mapping:
        return mapping[k]

    raise ValueError(f'Unsupported hotkey key: {key}')


def _parse_hotkey(hotkey: str) -> Tuple[int, int]:
    """Parse strings like 'ctrl+alt+d' into (modifiers, vkey)."""
    parts = [p.strip() for p in hotkey.replace('+', ' ').split() if p.strip()]
    mods = 0
    key = None
    for p in parts:
        lp = p.lower()
        if lp in ('ctrl', 'control'):
            mods |= MOD_CONTROL
        elif lp == 'alt':
            mods |= MOD_ALT
        elif lp == 'shift':
            mods |= MOD_SHIFT
        elif lp in ('win', 'super', 'meta', 'cmd'):
            mods |= MOD_WIN
        else:
            key = p
    if not key:
        raise ValueError(f'Hotkey missing main key: {hotkey}')
    vkey = _vk_code(key)
    return mods, vkey


class _MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt_x", wintypes.LONG),
        ("pt_y", wintypes.LONG),
    ]


class GlobalHotkeyFilter(QAbstractNativeEventFilter):
    def __init__(self, callbacks: Dict[int, Callable[[], None]]):
        super().__init__()
        self._callbacks = callbacks

    def nativeEventFilter(self, eventType, message):  # type: ignore[override]
        if eventType == 'windows_generic_MSG':
            msg = _MSG.from_address(int(message))
            if msg.message == WM_HOTKEY:
                hotkey_id = int(msg.wParam)
                cb = self._callbacks.get(hotkey_id)
                if cb:
                    try:
                        cb()
                    except Exception:
                        # Avoid breaking the filter on callback exception
                        pass
                return False, 0
        return False, 0


class GlobalHotkeys(QObject):
    """Windows global hotkeys via RegisterHotKey integrated with Qt event loop."""

    def __init__(self, app):
        super().__init__()
        self._app = app
        self._callbacks: Dict[int, Callable[[], None]] = {}
        self._filter = GlobalHotkeyFilter(self._callbacks)
        self._app.installNativeEventFilter(self._filter)

    def register(self, hotkey_id: int, hotkey: str, callback: Callable[[], None]) -> None:
        mods, vkey = _parse_hotkey(hotkey)
        # Unregister existing id if present
        if hotkey_id in self._callbacks:
            self.unregister(hotkey_id)
        if not user32.RegisterHotKey(None, hotkey_id, mods, vkey):
            raise OSError(f'RegisterHotKey failed for {hotkey}')
        self._callbacks[hotkey_id] = callback

    def unregister(self, hotkey_id: int) -> None:
        try:
            user32.UnregisterHotKey(None, hotkey_id)
        finally:
            self._callbacks.pop(hotkey_id, None)

    def unregister_all(self) -> None:
        for hotkey_id in list(self._callbacks.keys()):
            try:
                user32.UnregisterHotKey(None, hotkey_id)
            except Exception:
                pass
        self._callbacks.clear()

