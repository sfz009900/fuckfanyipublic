@echo off
echo 正在启动OCR翻译器...
python run.py
if %ERRORLEVEL% NEQ 0 (
    echo 启动失败，请确保已安装Python 3.7+
    pause
) 