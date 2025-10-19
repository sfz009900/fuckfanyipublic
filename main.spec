# -*- mode: python ; coding: utf-8 -*-


from PyInstaller.utils.hooks import collect_submodules

def optional_collect(name):
    try:
        return collect_submodules(name)
    except Exception:
        return []

# 尽量避免硬编码 venv 路径，使用默认 sys.path 搜索
a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        # PaddleOCR 英文模型（本仓库已包含 _infer 目录）
        ('en_PP-OCRv3_det_slim_infer', 'en_PP-OCRv3_det_slim_infer'),
        ('en_PP-OCRv3_rec_slim_infer', 'en_PP-OCRv3_rec_slim_infer'),
        ('en_PP-OCRv3_det_infer', 'en_PP-OCRv3_det_infer'),
        ('en_PP-OCRv3_rec_slim', 'en_PP-OCRv3_rec_slim'),
        ('en_PP-OCRv4_det_infer', 'en_PP-OCRv4_det_infer'),
        ('en_PP-OCRv4_rec_infer', 'en_PP-OCRv4_rec_infer'),

        # 旧目录（若代码回退时仍可用）
        ('en_number_mobile_v2.0_rec', 'en_number_mobile_v2.0_rec'),
        ('en_PP-OCRv3_det_slim', 'en_PP-OCRv3_det_slim'),

        # 程序资源
        ('assets', 'assets'),
        ('fonts', 'fonts'),
        ('config.ini', '.'),
    ],
    hiddenimports=(
        [
            # winrt OCR 相关
            'winrt.windows.foundation',
            'winrt.windows.foundation.collections',
            'winrt.windows.globalization',
            'winrt.windows.graphics.imaging',
            'winrt.windows.media.ocr',
            'winrt.windows.storage',
            'winrt.windows.storage.streams',

            # urllib3 v2 hface 子模块（避免运行时缺失）
            'urllib3.contrib.resolver.system',
            'urllib3.contrib.resolver',
            'urllib3.contrib',
            'urllib3.contrib.hface',
            'urllib3.contrib.hface.protocols',
            'urllib3.contrib.hface.protocols.http1',
            'urllib3.contrib.hface.protocols.http2',
            'urllib3.contrib.hface.protocols._protocols',
            'urllib3.contrib.hface.protocols._factories',
        ]
        # 尝试收集 paddleocr/paddle 可能的延迟导入模块（未安装时忽略）
        + optional_collect('paddleocr')
        + optional_collect('paddle')
    ),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
