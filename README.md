## 之前用的有道哪个截图翻译,它可以翻译后覆盖道原文的地方觉得挺方便的,后来好像复制原文需要收费,就自己弄了个自己用的,后来感觉挺方便的就开源了吧

# 功能介绍
  ## 1:截图翻译覆盖,按ctrl+alt+d进行截图翻译,翻译后界面如下,可以直接按O复制原文,C复制译文,R覆盖原文,和A AI学习
  <img width="1380" height="825" alt="image" src="https://github.com/user-attachments/assets/fc69c85e-cb84-447b-a0ce-4cef7d16ca96" />

  ### 覆盖原文效果如下:
  <img width="1380" height="915" alt="image" src="https://github.com/user-attachments/assets/799c89db-5abc-4ecc-87b6-1e979607d85f" />
  <img width="1917" height="996" alt="image" src="https://github.com/user-attachments/assets/983b276b-743e-4410-bea8-0cbdcfdf4c08" />

  ### 这里有多个翻译引擎可以自己配置:
  <img width="598" height="828" alt="image" src="https://github.com/user-attachments/assets/695e5e26-1190-49ff-9227-c1663803bb8c" />

  ### ollama下还可以自定义翻译情景,比如这样:
  <img width="611" height="915" alt="image" src="https://github.com/user-attachments/assets/9ad9342b-d6fe-4c4c-9788-c05b3654b7b6" />

 ## 2:AI学习功能,这是我自己觉得方便记忆弄的,此功能在AI截图翻译直接按A可以自动跳过去,或者直接按ctrl+alt+x,这个是调用的本地的ollama的"gpt-oss:120b-cloud",效果如下:
   <img width="785" height="722" alt="image" src="https://github.com/user-attachments/assets/74055220-51ab-45fa-8018-a92c29920f19" />
   <img width="778" height="727" alt="image" src="https://github.com/user-attachments/assets/424955b9-0d37-4eff-a7c1-8ba96ed8d60f" />
   <img width="780" height="722" alt="image" src="https://github.com/user-attachments/assets/f6a9b8a3-4b49-4828-a737-7501d366e81e" />

 ## 支持高亮匹配显示:
 <img width="777" height="723" alt="image" src="https://github.com/user-attachments/assets/23146b31-d70d-4631-82e4-89f61e55ef40" />

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

- 我用的Python 3.10.5
- Windows操作系统

### 安装步骤

1. 克隆或下载本仓库
2. 运行安装脚本安装依赖

```
python -m venv .venv
.venv\Scripts\activate
pip install -r .\requirements.txt
python .\main.py
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
