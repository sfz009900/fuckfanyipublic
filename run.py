"""
OCR翻译器启动脚本
"""
import os
import sys
import subprocess
import importlib.util

def check_module(module_name):
    """检查模块是否已安装"""
    return importlib.util.find_spec(module_name) is not None

def install_dependency():
    """运行依赖安装脚本"""
    install_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "install_dependencies.py")
    if os.path.exists(install_script):
        subprocess.call([sys.executable, install_script])
    else:
        print("错误：找不到安装脚本 install_dependencies.py")
        sys.exit(1)

def main():
    """主函数"""
    # 检查PaddleOCR是否已安装
    if not check_module("paddleocr"):
        print("检测到PaddleOCR未安装，将安装所需依赖...")
        install_dependency()
    
    # 检查OpenCV是否已安装
    if not check_module("cv2"):
        print("检测到OpenCV未安装，将安装所需依赖...")
        install_dependency()
    
    # 检查PyQt5是否已安装
    if not check_module("PyQt5"):
        print("检测到PyQt5未安装，将安装所需依赖...")
        install_dependency()
    
    # 启动主程序
    main_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
    if os.path.exists(main_script):
        subprocess.call([sys.executable, main_script])
    else:
        print("错误：找不到主程序文件 main.py")
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n程序已终止")
    except Exception as e:
        print(f"运行时出错: {e}")
        input("按回车键退出...") 