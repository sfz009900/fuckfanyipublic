"""
Compatibility shim for the removed stdlib module `imghdr` (PEP 594).
Provides a minimal `what(file, h=None)` API sufficient for libraries
that just need to recognize common image formats. Internally uses Pillow.
"""
from typing import Optional, Union


def what(file: Optional[Union[str, bytes]] = None, h: Optional[bytes] = None) -> Optional[str]:
    try:
        from PIL import Image
        from io import BytesIO

        if h is not None:
            img = Image.open(BytesIO(h))
        else:
            if file is None:
                return None
            img = Image.open(file)  # type: ignore[arg-type]

        fmt = (img.format or "").lower()
        # Map Pillow names to legacy imghdr labels where they differ.
        mapping = {
            "jpeg": "jpeg",
            "png": "png",
            "gif": "gif",
            "bmp": "bmp",
            "tiff": "tiff",
            "webp": "webp",
            "ppm": "pbm",
            "pgm": "pgm",
            "pbm": "pbm",
            "pnm": "pbm",
            "tga": "tga",
            "ico": "ico",
        }
        return mapping.get(fmt, fmt or None)
    except Exception:
        return None


__all__ = ["what"]

