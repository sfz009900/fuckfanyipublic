"""
依赖安装脚本 - 安装OCR翻译器所需的依赖库
"""
import subprocess
import sys
import os

def install_package(package):
    """安装指定的Python包"""
    try:
        print(f"正在安装 {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", package])
        print(f"{package} 安装成功！")
        return True
    except subprocess.CalledProcessError as e:
        print(f"安装 {package} 时出错: {str(e)}")
        return False

def main():
    """主函数 - 安装所有依赖"""
    print("开始安装OCR翻译器所需依赖...")
    
    # 基础依赖
    basic_deps = [
        "pillow",
        "numpy",
        "opencv-python",
        "PyQt5",
        "keyboard",
        "pywin32",
        "configparser",
        "nest_asyncio",
    ]
    
    # PaddleOCR依赖
    paddle_deps = [
        "paddlepaddle",  # CPU版本的PaddlePaddle
        "paddleocr",     # PaddleOCR工具包
    ]
    
    # 安装基础依赖
    print("\n=== 安装基础依赖 ===")
    for dep in basic_deps:
        install_package(dep)
    
    # 安装PaddleOCR依赖
    print("\n=== 安装PaddleOCR依赖 ===")
    for dep in paddle_deps:
        install_package(dep)
    
    print("\n所有依赖安装完成！")
    print("如果需要使用GPU加速，请手动安装适合您系统的GPU版本PaddlePaddle。")
    print("详情请参考: https://www.paddlepaddle.org.cn/install/quick")
    
    input("\n按回车键退出...")

if __name__ == "__main__":
    main() 