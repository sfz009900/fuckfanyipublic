# OCR翻译器

一个用于截图翻译的桌面工具，使用PaddleOCR进行文字识别，并通过多种翻译引擎提供翻译服务。

## 功能特性

- 使用PaddleOCR进行高精度文字识别，支持多语言
- 支持多种翻译引擎（Ollama、OpenAI、Google、Microsoft等）
- 截图选择区域进行OCR识别和翻译
- 结果显示窗口支持复制、调整和覆盖原文
  - 覆盖原文(R)：默认启用“智能覆盖”模式，会先清理原文文本再渲染译文，尽量保留背景纹理，效果更贴近“原文被直接翻译”的观感。
  - 可在 `config.ini` 的 `[OVERLAY]` 部分通过 `overlay_mode = inpaint|box` 切换；`overlay_auto_text_color = True` 时自动选择黑/白字以保证可读性。
- 翻译历史记录保存和查看
- 系统托盘图标方便操作
- 全局热键快速截图

## 安装指南

### 环境要求

- Python 3.7+
- Windows操作系统

### 安装步骤

1. 克隆或下载本仓库
2. 运行安装脚本安装依赖

```
python install_dependencies.py
```

3. 安装完成后，运行主程序

```
python main.py
```

## 使用方法

1. 启动程序后，它会在系统托盘中显示图标
2. 按下默认热键 `Ctrl+Alt+D` 进行截图（可在配置文件中修改）
3. 在屏幕上选择要识别的文本区域
4. 程序会自动识别文本并翻译，显示在结果窗口中
5. 可以在结果窗口中复制翻译文本或原文

## 配置说明

配置文件位于程序根目录的 `config.ini`，您可以修改以下设置：

### OCR设置

```ini
[PADDLEOCR]
ocr_language = en          # OCR语言，如en、ch等
ocr_use_angle_cls = True   # 是否检测文字方向
ocr_dynamic_cls = True     # 动态开启角度分类（直立文本更快）
ocr_cls_min_angle = 1.0    # 动态分类的最小角度阈值（度）
ocr_use_gpu = False        # 是否使用GPU（支持自动检测）
ocr_auto_use_gpu = True    # 自动检测CUDA并启用GPU
ocr_enable_mkldnn = True   # CPU下启用MKLDNN加速
ocr_cpu_num_threads = 4    # CPU推理线程数（MKLDNN时生效）
ocr_timeout = 30           # OCR超时时间
ocr_show_log = False       # 显示详细日志（默认关闭以提速）

# 识别/检测精度&速度参数
ocr_rec_batch_num = 10     # 识别批大小（更大更快，内存更高）
ocr_drop_score = 0.5       # 低分过滤阈值（提高准确率）
ocr_det_limit_side_len = 960  # 检测输入长边限制
ocr_max_input_side = 1600  # 预处理阶段输入最大边长
```

### 翻译设置

可以在 `[OCR_TRANSLATION]` 部分配置翻译设置，包括源语言、目标语言和翻译引擎等。

## 常见问题

- **Q: 安装PaddleOCR时出错怎么办？**
  A: 请参考[PaddleOCR官方文档](https://github.com/PaddlePaddle/PaddleOCR/blob/release/2.6/doc/doc_ch/quickstart.md)进行安装

- **Q: 如何修改截图热键？**
  A: 在config.ini文件的[HOTKEYS]部分修改screenshot_hotkey配置项

## 许可证

MIT License

## 鸣谢

- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) - 提供OCR识别引擎
- 各翻译API提供商 
