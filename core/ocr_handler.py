import asyncio
import sys
import threading
import io
import numpy as np
from PIL import Image, ImageEnhance
import os
import nest_asyncio
from config_manager import config
from utils.logger import get_logger
import re
import time

logger = get_logger(__name__)

# 添加sklearn导入
try:
    from sklearn.cluster import KMeans
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("警告: sklearn未安装，将使用简化的分段算法")

# 添加PaddleOCR导入，使用try-except防止导入错误（输出真实异常以便排查打包问题）
try:
    from paddleocr import PaddleOCR  # type: ignore
    PADDLEOCR_AVAILABLE = True
except Exception as e:  # ImportError 或其依赖的导入失败都会到这里
    PADDLEOCR_AVAILABLE = False
    print(f"警告: PaddleOCR导入失败（可能未安装或缺少依赖）: {e}")

class OCRHandler:
    def __init__(self):
        self.ocr_errors = 0
        self.max_retries = config.get('OCR_TRANSLATION', 'MAX_RETRIES', 3)
        self.ocr_timeout = config.get('PADDLEOCR', 'OCR_TIMEOUT', 30)
        self._lock = threading.Lock()
        self._thread_local = threading.local()
        # 调试输出开关（减少控制台IO以提升速度）
        self.debug = bool(config.get('PADDLEOCR', 'OCR_SHOW_LOG', False))
        # 允许嵌套使用事件循环
        nest_asyncio.apply()
        # 初始化OCR引擎
        self._initialize_ocr()

    def _get_event_loop(self):
        """Get or create an event loop for the current thread"""
        if not hasattr(self._thread_local, 'loop'):
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            self._thread_local.loop = loop
        return self._thread_local.loop

    def _initialize_ocr(self):
        """Initialize OCR engine"""
        if not PADDLEOCR_AVAILABLE:
            logger.error("PaddleOCR未安装，请运行install_dependencies.py安装依赖")
            logger.info("您可以尝试手动安装: pip install paddlepaddle paddleocr")
            return
            
        try:
            # 从配置中读取OCR设置
            # 自动检测GPU可用性
            auto_use_gpu = config.get('PADDLEOCR', 'OCR_AUTO_USE_GPU', True)
            use_gpu = config.get('PADDLEOCR', 'OCR_USE_GPU', False)
            if auto_use_gpu:
                try:
                    import paddle  # type: ignore
                    if hasattr(paddle, 'device') and paddle.device.is_compiled_with_cuda():
                        use_gpu = True
                        if self.debug:
                            logger.info("检测到CUDA支持，已自动启用GPU")
                except Exception:
                    # 保持用户配置
                    pass
            use_angle_cls = config.get('PADDLEOCR', 'OCR_USE_ANGLE_CLS', True)
            lang = config.get('PADDLEOCR', 'OCR_LANGUAGE', 'en')
            show_log = config.get('PADDLEOCR', 'OCR_SHOW_LOG', False)
            enable_mkldnn = config.get('PADDLEOCR', 'OCR_ENABLE_MKLDNN', True)
            
            # 读取高级参数
            cls_batch_num = config.get('PADDLEOCR', 'OCR_CLS_BATCH_NUM', 1)
            rec_batch_num = config.get('PADDLEOCR', 'OCR_REC_BATCH_NUM', 6)
            det_db_thresh = config.get('PADDLEOCR', 'OCR_DET_DB_THRESH', 0.3)
            det_db_box_thresh = config.get('PADDLEOCR', 'OCR_DET_DB_BOX_THRESH', 0.5)
            max_text_length = config.get('PADDLEOCR', 'OCR_MAX_TEXT_LENGTH', 50)
            drop_score = config.get('PADDLEOCR', 'OCR_DROP_SCORE', 0.5)
            det_limit_side_len = config.get('PADDLEOCR', 'OCR_DET_LIMIT_SIDE_LEN', 960)

            # CPU线程优化（仅CPU且启用MKLDNN时）
            if enable_mkldnn and not use_gpu:
                try:
                    cpu_threads = int(config.get('PADDLEOCR', 'OCR_CPU_NUM_THREADS', max(2, min(4, os.cpu_count() or 2))))
                    os.environ.setdefault('OMP_NUM_THREADS', str(cpu_threads))
                    os.environ.setdefault('MKL_NUM_THREADS', str(cpu_threads))
                    if self.debug:
                        logger.info(f"设置CPU线程数: {cpu_threads}")
                except Exception:
                    pass
            
            # 优先使用本地模型目录（若存在）以避免重复下载并提升初始化速度
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            det_dir_candidates = [
                os.path.join(project_root, f"{lang}_PP-OCRv4_det_infer"),
                os.path.join(project_root, f"{lang}_PP-OCRv3_det_slim_infer"),
                os.path.join(project_root, f"{lang}_PP-OCRv3_det_infer"),
            ]
            rec_dir_candidates = [
                os.path.join(project_root, f"{lang}_PP-OCRv4_rec_infer"),
                os.path.join(project_root, f"{lang}_PP-OCRv3_rec_slim_infer"),
                os.path.join(project_root, f"{lang}_PP-OCRv3_rec_infer"),
            ]

            det_model_dir = next((d for d in det_dir_candidates if os.path.isdir(d)), None)
            rec_model_dir = next((d for d in rec_dir_candidates if os.path.isdir(d)), None)

            ocr_kwargs = dict(
                use_gpu=use_gpu,
                use_angle_cls=use_angle_cls,
                lang=lang,
                show_log=show_log,
                enable_mkldnn=enable_mkldnn,
                cls_batch_num=cls_batch_num,
                rec_batch_num=rec_batch_num,
                det_db_thresh=det_db_thresh,
                det_db_box_thresh=det_db_box_thresh,
                max_text_length=max_text_length,
                drop_score=drop_score,
                det_limit_side_len=det_limit_side_len,
            )
            if det_model_dir and rec_model_dir:
                ocr_kwargs.update({
                    'det_model_dir': det_model_dir,
                    'rec_model_dir': rec_model_dir,
                })
                logger.info(f"使用本地OCR模型: det={det_model_dir}, rec={rec_model_dir}")
            else:
                logger.info("未检测到本地OCR模型目录，使用默认在线模型")

            # 初始化PaddleOCR引擎
            self.ocr_engine = PaddleOCR(**ocr_kwargs)
            logger.info(f"PaddleOCR初始化成功，语言：{lang}，GPU={use_gpu}, MKLDNN={enable_mkldnn}, rec_batch={rec_batch_num}")
        except Exception as e:
            logger.error(f"PaddleOCR初始化失败: {e}")
            logger.error("程序将退出")
            sys.exit(1)

    @staticmethod
    def _convert_to_pil_image(image):
        """Convert various image formats to PIL Image"""
        if isinstance(image, np.ndarray):
            # Convert numpy array to PIL Image
            return Image.fromarray(np.uint8(image))
        elif isinstance(image, Image.Image):
            return image
        else:
            raise ValueError(f"不支持的图像类型: {type(image)}")

    @staticmethod
    def optimize_image_for_ocr(image):
        """Optimize image for better OCR recognition"""
        try:
            # Convert to PIL Image if needed
            image = OCRHandler._convert_to_pil_image(image)
            
            # Ensure correct image mode
            if image.mode not in ['RGB', 'L']:
                image = image.convert('RGB')
            
            # Adjust image size: scale up tiny regions and cap huge sides to reduce compute
            min_height = 50
            min_width = 200
            max_side = int(config.get('PADDLEOCR', 'OCR_MAX_INPUT_SIDE', 1600))
            current_width, current_height = image.size
            scale_up = max(min_height/current_height, min_width/current_width, 1)
            scale_down = min(1.0, max_side / max(current_width, current_height))
            scale = scale_up * scale_down
            if abs(scale - 1.0) > 1e-3:
                new_width = max(1, int(current_width * scale))
                new_height = max(1, int(current_height * scale))
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # 根据配置调整图像预处理
            enable_preprocessing = config.get('IMAGE_PROCESSING', 'ENABLE_PREPROCESSING', True)
            if enable_preprocessing:
                # Optional deskew to improve OCR on rotated text
                try:
                    if config.get('IMAGE_PROCESSING', 'DESKEW_ENABLED', True):
                        image = OCRHandler._deskew_image(image)
                except Exception:
                    pass
                # 增强对比度
                contrast_alpha = config.get('IMAGE_PROCESSING', 'CONTRAST_ALPHA', 1.3)
                enhancer = ImageEnhance.Contrast(image)
                image = enhancer.enhance(contrast_alpha)
                
                # 增强锐度
                enhancer = ImageEnhance.Sharpness(image)
                image = enhancer.enhance(1.5)
                
                # 调整亮度
                enhancer = ImageEnhance.Brightness(image)
                image = enhancer.enhance(1.2)
            
            return image
        except Exception as e:
            if logger:
                logger.debug(f"图像优化失败: {str(e)}")
            return OCRHandler._convert_to_pil_image(image)  # 返回原始图像作为PIL图像

    @staticmethod
    def _deskew_image(pil_img):
        """Deskew a PIL image using edge-based angle estimation."""
        import cv2
        import numpy as np
        # Convert to grayscale
        img = np.array(pil_img)
        if img.ndim == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        else:
            gray = img
        # Edge detection
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLines(edges, 1, np.pi / 180.0, 120)
        angle = 0.0
        if lines is not None and len(lines) > 0:
            angles = []
            for rho, theta in lines[:,0]:
                a = theta
                # Map angle to [-90, 90)
                ang = (a * 180.0 / np.pi) - 90.0
                if -45 <= ang <= 45:
                    angles.append(ang)
            if angles:
                angle = float(np.median(angles))
        if abs(angle) < 0.5:
            return pil_img
        # Rotate to deskew
        (h, w) = gray.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        return Image.fromarray(rotated)

    @staticmethod
    def _estimate_rotation_angle(pil_img, max_side=640):
        """快速估计文本旋转角度（单位：度）。"""
        try:
            import cv2
            import numpy as np
            img = np.array(pil_img)
            if img.ndim == 3:
                gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
            else:
                gray = img
            h, w = gray.shape[:2]
            scale = min(1.0, float(max_side) / max(h, w))
            if scale < 1.0:
                gray = cv2.resize(gray, (int(w*scale), int(h*scale)), interpolation=cv2.INTER_AREA)
            edges = cv2.Canny(gray, 50, 150)
            lines = cv2.HoughLines(edges, 1, np.pi / 180.0, 120)
            if lines is None or len(lines) == 0:
                return 0.0
            angles = []
            for rho, theta in lines[:,0]:
                ang = (theta * 180.0 / np.pi) - 90.0
                if -45 <= ang <= 45:
                    angles.append(ang)
            if not angles:
                return 0.0
            return float(np.median(angles))
        except Exception:
            return 0.0

    @staticmethod
    def _split_english_text(text):
        """对英文文本进行分词处理
        
        处理类似"OnSundaynight,IwillgiveatalkinWisconsin."这样的连续英文文本，
        尝试将其分割为正确的单词序列
        """
        if not text or not any(c.isalpha() for c in text):
            return text
        
        if any('\u4e00' <= c <= '\u9fff' for c in text):
            return text  # 如果含有中文字符，不处理
        
        # 1. 使用常见单词列表匹配
        common_words = [
            "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday",
            "night", "morning", "evening", "afternoon", "January", "February", "March", 
            "April", "May", "June", "July", "August", "September", "October", "November", 
            "December", "give", "talk", "Wisconsin", "Chicago", "York", "Angeles", "will",
            "would", "could", "should", "have", "been", "were", "into", "onto", "today",
            "tomorrow", "yesterday", "the", "and", "for", "with", "that", "this", "from",
            "there", "their", "they", "them", "these", "those", "every", "each", "some",
            "where", "when", "what", "who", "why", "how", "which", "whom", "whose"
        ]
        
        # 按照大写字母分割文本
        result = ""
        current_word = ""
        
        for i, char in enumerate(text):
            current_word += char
            
            # 检查是否到达单词边界
            if i < len(text) - 1:
                next_char = text[i + 1]
                
                # 如果当前字符是字母，下一个是标点或空格，视为单词结束
                if char.isalpha() and (next_char in ",.!?;: "):
                    # 检查当前单词是否匹配常见单词
                    for word in common_words:
                        if current_word.lower() == word.lower():
                            result += current_word + " "
                            current_word = ""
                            break
                        # 部分匹配也可以考虑
                        elif len(current_word) >= 3 and word.lower().startswith(current_word.lower()):
                            # 这可能是单词的一部分
                            continue
                    
                    # 如果没有匹配到常见单词
                    if current_word:
                        # 检查是否是大写开头，可能是名词
                        if current_word[0].isupper():
                            result += current_word + " "
                            current_word = ""
                
                # 如果当前是小写字母，下一个是大写字母，可能是两个单词的分界
                elif char.islower() and next_char.isupper():
                    result += current_word + " "
                    current_word = ""
                
                # 如果当前是大写字母且不是首字母，下一个是小写字母，可能是单词的一部分
                elif i > 0 and char.isupper() and next_char.islower():
                    if text[i-1].isupper():  # 连续的大写字母，可能是缩写
                        continue
                    # 将大写字母视为新单词的开始
                    result += current_word[:-1] + " " + current_word[-1]
                    current_word = ""
        
        # 处理最后一个单词
        if current_word:
            result += current_word
        
        # 对结果进行清理
        result = result.replace(" ,", ",").replace(" .", ".").replace(" !", "!").replace(" ?", "?")
        result = result.replace("  ", " ").strip()
        
        # 处理特殊情况 - I开头的短语
        result = result.replace("I will", "I will")
        result = result.replace("I am", "I am")
        result = result.replace("I have", "I have")
        
        return result

    def perform_ocr(self, image):
        """使用PaddleOCR对图像进行OCR识别"""
        if not PADDLEOCR_AVAILABLE:
            print("错误: PaddleOCR未安装，无法执行OCR")
            return ""
            
        try:
            with self._lock:
                # 优化图像
                image_opt = self.optimize_image_for_ocr(image)
                
                # 将PIL图像转换为numpy数组
                if isinstance(image_opt, Image.Image):
                    image_array = np.array(image_opt)
                else:
                    image_array = image_opt
                
                # 动态决定是否使用角度分类（速度与准确权衡）
                dynamic_cls = bool(config.get('PADDLEOCR', 'OCR_DYNAMIC_CLS', True))
                apply_cls = True
                if dynamic_cls and config.get('PADDLEOCR', 'OCR_USE_ANGLE_CLS', True):
                    angle = self._estimate_rotation_angle(image_opt)
                    apply_cls = abs(angle) >= float(config.get('PADDLEOCR', 'OCR_CLS_MIN_ANGLE', 1.0))
                    if self.debug:
                        logger.info(f"估计旋转角度={angle:.2f}°, 应用角度分类={apply_cls}")
                else:
                    apply_cls = config.get('PADDLEOCR', 'OCR_USE_ANGLE_CLS', True)

                # 使用PaddleOCR进行OCR识别
                result = self.ocr_engine.ocr(image_array, cls=apply_cls)
                
                # 处理OCR结果
                text = ""
                if self.debug:
                    print(f"PaddleOCR识别结果: {result}")
                
                if result is not None and len(result) > 0:
                    # 保存识别到的各行文本及其位置信息
                    text_lines = []
                    
                    # 根据PaddleOCR 2.6以上版本API调整结果解析方式
                    for line_result in result:
                        if not line_result:
                            continue
                            
                        for item in line_result:
                            if isinstance(item, list) and len(item) >= 2:
                                coordinates = item[0]  # 坐标信息
                                line_text = item[1][0]  # 文本内容在[1][0]
                                confidence = item[1][1]  # 置信度在[1][1]
                                if confidence > float(config.get('PADDLEOCR', 'OCR_DROP_SCORE', 0.5)):  # 只保留置信度超过阈值的结果
                                    # 应用英文分词处理（可配置）
                                    if bool(config.get('PADDLEOCR', 'OCR_ENABLE_EN_SPLIT', True)):
                                        processed_text = self._split_english_text(line_text)
                                    else:
                                        processed_text = line_text
                                    # 记录文本位置信息和内容
                                    y_center = (coordinates[0][1] + coordinates[2][1]) / 2
                                    text_lines.append((y_center, processed_text, coordinates))
                    
                    # 按y坐标排序
                    text_lines.sort(key=lambda x: x[0])
                    
                    # 打印原始识别结果（调试）
                    if self.debug:
                        print("原始识别行:")
                        for i, (y, text, _) in enumerate(text_lines):
                            print(f"行{i+1}: y={y:.2f}, 文本: {text}")
                    
                    # 基于Y坐标的段落分段 - 直接使用OCR识别结果的位置信息
                    # 分析Y坐标差异的分布，以便更智能地确定段落分隔阈值
                    y_diffs = []  # 初始化y_diffs变量
                    if len(text_lines) > 1:
                        # 计算相邻行之间的Y坐标差异
                        y_diffs = [text_lines[i+1][0] - text_lines[i][0] for i in range(len(text_lines)-1)]
                        if self.debug:
                            print(f"相邻行Y坐标差异: {', '.join([f'{diff:.2f}' for diff in y_diffs])}")
                        
                        # 根据行距的聚类识别段落
                        # 先对行距进行排序
                        sorted_diffs = sorted(y_diffs)
                        
                        # 如果至少有两个行距
                        if len(sorted_diffs) >= 2:
                            # 使用K-means聚类分析行距
                            # 将行距分为两组：段落内行距和段落间行距
                            
                            try:
                                # 判断是否有sklearn库
                                if SKLEARN_AVAILABLE:
                                    kmeans = KMeans(n_clusters=2, random_state=0).fit([[x] for x in sorted_diffs])
                                    labels = kmeans.labels_
                                    
                                    # 分组
                                    group_0 = [sorted_diffs[i] for i in range(len(sorted_diffs)) if labels[i] == 0]
                                    group_1 = [sorted_diffs[i] for i in range(len(sorted_diffs)) if labels[i] == 1]
                                    
                                    # 确定哪个组是段落内行距（值较小的组）
                                    if sum(group_0) / len(group_0) < sum(group_1) / len(group_1):
                                        small_group = group_0
                                        large_group = group_1
                                    else:
                                        small_group = group_1
                                        large_group = group_0
                                else:
                                    # 如果没有sklearn，使用简化的分组方法
                                    if self.debug:
                                        print("使用简化的分组方法进行行距分析")
                                    # 使用中位数作为分隔点
                                    median_idx = len(sorted_diffs) // 2
                                    small_group = sorted_diffs[:median_idx]
                                    large_group = sorted_diffs[median_idx:]
                                
                                # 计算两组的中心点
                                small_center = sum(small_group) / len(small_group)
                                large_center = sum(large_group) / len(large_group) if large_group else float('inf')
                                
                                if self.debug:
                                    print(f"聚类结果: 小组(段落内)={small_group}, 大组(段落间)={large_group}")
                                    print(f"小组中心={small_center:.2f}, 大组中心={large_center:.2f}")
                                
                                # 3. 判断聚类结果是否有效
                                if small_group and large_group and large_center > small_center * 1.3:
                                    # 聚类有效，使用两组的中点作为阈值
                                    paragraph_threshold = (small_center + large_center) / 2
                                    if self.debug:
                                        print(f"行距聚类: 段落内行距={small_center:.2f}, 段落间行距={large_center:.2f}, 阈值={paragraph_threshold:.2f}")
                                else:
                                    # 聚类无效，检查行距分布
                                    avg_diff = sum(y_diffs) / len(y_diffs)
                                    std_diff = (sum((diff - avg_diff) ** 2 for diff in y_diffs) / len(y_diffs)) ** 0.5
                                    
                                    # 如果行距标准差很小，考虑文本内容而不是立即判定为独立段落
                                    if std_diff < avg_diff * 0.2 or not large_group:
                                        # 不立即将paragraph_threshold设为极大值
                                        # 改为设置为平均行距的两倍，后续会优先使用语义分析判断
                                        paragraph_threshold = avg_diff * 2
                                        if self.debug:
                                            print(f"行距分布均匀，将优先使用语义分析判断段落，阈值设为{paragraph_threshold:.2f}")
                                    else:
                                        # 使用平均值作为阈值
                                        paragraph_threshold = avg_diff * 1.3
                                        if self.debug:
                                            print(f"使用平均行距的1.3倍作为阈值: {paragraph_threshold:.2f}")
                            except Exception as e:
                                if self.debug:
                                    print(f"聚类分析出错: {e}，使用简单阈值")
                                # 使用简单阈值
                                avg_diff = sum(y_diffs) / len(y_diffs)
                                paragraph_threshold = avg_diff * 1.3
                                if self.debug:
                                    print(f"使用平均行距的1.3倍作为阈值: {paragraph_threshold:.2f}")
                        else:
                            # 只有一个行距，直接使用两倍作为阈值
                            paragraph_threshold = sorted_diffs[0] * 2
                            if self.debug:
                                print(f"只有一个行距，使用两倍作为阈值: {paragraph_threshold:.2f}")
                    else:
                        # 只有一行文本，不需要分段
                        paragraph_threshold = float('inf')
                    
                    # 基于Y坐标差异分组行
                    y_based_paragraphs = []
                    current_paragraph_lines = []
                    
                    # 如果设置为无穷大，表示每行需要单独分析
                    if paragraph_threshold == float('inf'):
                        # 这里将不再简单地返回独立段落，而是进行语义连贯性分析
                        if self.debug:
                            print("段落阈值设为无穷大，但仍将进行语义连贯性分析")
                        # 重新设置一个较大的阈值，但不是无穷大，让后续分析能够进行
                        paragraph_threshold = max(y_diffs) * 2 if y_diffs else 50
                    
                    # 增加基于内容的智能判断
                    for i, (y_center, line_text, coords) in enumerate(text_lines):
                        # 第一行总是新段落的开始
                        if i == 0:  
                            current_paragraph_lines.append(line_text)
                            continue
                            
                        # 计算与前一行的Y坐标差异
                        prev_y = text_lines[i-1][0]
                        y_diff = y_center - prev_y
                        prev_text = text_lines[i-1][1]
                        
                        # 特征检测：基于语法和格式特征判断是否为独立段落
                        is_new_paragraph = False
                        is_semantically_connected = False  # 确保变量在所有条件分支之前已初始化
                        
                        # 1. Y坐标差异大于阈值，可能是新段落
                        if y_diff > paragraph_threshold:
                            is_new_paragraph = True
                            if self.debug:
                                print(f"行{i+1}与上一行Y差异为{y_diff:.2f}，大于阈值{paragraph_threshold:.2f}，识别为新段落")
                        
                        # 2. 检测冒号格式的列表项或选项列表
                        elif (re.match(r'^[A-Za-z][A-Za-z\s]*(AI|API)?(\s+\([^)]+\))?\s*[:：]', line_text) or  # 检测"Open AI:"等格式
                              re.match(r'^[A-Za-z\s]+[:：]', line_text) or  # 简化的冒号格式
                              (line_text.split() and ":" in line_text.split()[0])):  # 第一个词包含冒号
                            is_new_paragraph = True
                            if self.debug:
                                print(f"行{i+1}被识别为冒号格式列表项，应为独立段落: {line_text}")
                        
                        # 3. 检查前一行是否为冒号格式的列表项，这通常意味着当前行应该是新段落
                        elif prev_text and (":" in prev_text or "：" in prev_text):
                            is_new_paragraph = True
                            if self.debug:
                                print(f"行{i+1}的前一行含有冒号，应为独立段落: {prev_text} -> {line_text}")
                        
                        # 4. 当前行或上一行以特定模式结束，可能是列表项
                        elif (line_text.rstrip().endswith((':', '：', ' -', '...', '…', '♦', '•', '⦿', '◉', '◈', '▶'))
                            or prev_text.rstrip().endswith((':', '：', ' -', '...', '…', '♦', '•', '⦿', '◉', '◈', '▶'))
                            or re.match(r'^[\d]+\.\s+', line_text.strip()) # 数字编号开头，如 "1. "
                            or re.match(r'^[A-Za-z]\.\s+', line_text.strip()) # 字母编号开头，如 "A. "
                            or (prev_text.strip() and line_text.strip() and line_text[0].isupper() and 
                                prev_text[-1] in ['.', '!', '?', '。', '！', '？'])):
                            is_new_paragraph = True
                            if self.debug:
                                print(f"行{i+1}基于内容特征识别为新段落: {line_text}")
                            
                        # 5. 检测括号中的特定短语，如"click to expand"通常表示独立项
                        elif re.search(r'\([^\)]*click[^\)]*\)', line_text.lower()) or re.search(r'\([^\)]*expand[^\)]*\)', line_text.lower()):
                            is_new_paragraph = True
                            if self.debug:
                                print(f"行{i+1}包含展开提示，识别为独立项: {line_text}")
                            
                        # 6. 检测上下文连贯性
                        else:
                            # 获取前一行的最后一个单词和当前行的第一个单词
                            prev_words = prev_text.split()
                            current_words = line_text.split()
                            
                            # 首先检查段落语义连贯性
                            is_semantically_connected = False
                            
                            if prev_words and current_words:
                                # 首先检查特殊情况：明显的句子不完整情况
                                # a. 前一行以连词、介词等结束
                                connecting_words = ['a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 
                                                  'with', 'for', 'by', 'as', 'from', 'of', 'that', 'which', 'who']
                                
                                last_word = prev_words[-1].lower().rstrip(',.;:')
                                if last_word in connecting_words:
                                    is_semantically_connected = True
                                    if self.debug:
                                        print(f"行{i+1}与上一行存在明显连贯性(连接词): {prev_text} -> {line_text}")
                                
                                # b. 检查句子不完整: 没有结束标点且前一行不包含冒号
                                elif not prev_text.rstrip()[-1] in ['.', '!', '?', '。', '！', '？', ';', '；', ':', '：'] and not (":" in prev_text or "：" in prev_text):
                                    is_semantically_connected = True
                                    if self.debug:
                                        print(f"行{i+1}与上一行存在明显连贯性(不完整句子): {prev_text} -> {line_text}")
                                
                                # c. 当前行首字母小写（非专有名词），通常表示句子延续
                                elif current_words[0][0].islower() and not re.match(r'^[a-z]+\.$', current_words[0]):
                                    is_semantically_connected = True
                                    if self.debug:
                                        print(f"行{i+1}与上一行存在明显连贯性(小写开头): {prev_text} -> {line_text}")
                                    
                                # d. 检查技术文档特有的连贯性：如前一行结束词是技术词汇，当前行以技术词汇开始
                                elif (re.search(r'(artificial|security|intelligence|testing|analysis)$', prev_text.lower()) and
                                      re.search(r'^(intelligence|technologies|framework|system|engine|tool)', line_text.lower())):
                                    is_semantically_connected = True
                                    if self.debug:
                                        print(f"行{i+1}与上一行存在技术内容连贯性: {prev_text} -> {line_text}")
                                
                                # e. 前一行以破折号、逗号结束
                                elif prev_text.rstrip()[-1] in ['-', ',', '，']:
                                    is_semantically_connected = True
                                    if self.debug:
                                        print(f"行{i+1}与上一行存在标点连贯性: {prev_text} -> {line_text}")
                                
                                # f. 前一行太短（通常不是完整句子）且不是标题格式
                                elif len(prev_text.strip()) < 40 and not re.match(r'^[A-Z][a-z]+(\s+[A-Z][a-z]+)*$', prev_text.strip()):
                                    # 检查是否符合标题模式（每个单词首字母大写）且不含冒号
                                    if not all(w[0].isupper() for w in prev_text.split() if w and w[0].isalpha()) and not (":" in prev_text or "：" in prev_text):
                                        is_semantically_connected = True
                                        if self.debug:
                                            print(f"行{i+1}与上一行可能连贯(前一行较短): {prev_text} -> {line_text}")
                                
                                # g. 检查明显的句子断开：前一行结束词与当前行开始词组合很常见
                                last_two_words = " ".join(prev_words[-2:]) if len(prev_words) >= 2 else prev_words[-1] if prev_words else ""
                                first_two_words = " ".join(current_words[:2]) if len(current_words) >= 2 else current_words[0] if current_words else ""
                                combined_phrase = f"{last_two_words} {first_two_words}".lower()
                                
                                common_phrases = [
                                    "artificial intelligence", "security testing", "information security", 
                                    "cutting edge", "edge technologies", "security professionals", 
                                    "who need", "need a", "a powerful", "flexible solution"
                                ]
                                
                                for phrase in common_phrases:
                                    if phrase in combined_phrase:
                                        is_semantically_connected = True
                                        if self.debug:
                                            print(f"行{i+1}与上一行存在短语连贯性: '{phrase}' in '{combined_phrase}'")
                                        break
                        
                        # 根据语义连贯性结果设置段落标志
                        # 先定义默认值，防止在某些分支中没有定义导致错误
                        is_semantically_connected = False if 'is_semantically_connected' not in locals() else is_semantically_connected
                        
                        if is_semantically_connected:
                            is_new_paragraph = False
                        # 如果Y差异小于阈值的70%且没有明确的段落特征，可能是同一段落内的换行
                        elif y_diff < paragraph_threshold * 0.7 and not is_new_paragraph:
                            is_new_paragraph = False
                            if self.debug:
                                print(f"行{i+1}与上一行Y差异小({y_diff:.2f})，视为同一段落: {prev_text} -> {line_text}")
                        elif not is_new_paragraph:
                            is_new_paragraph = True
                            if self.debug:
                                print(f"行{i+1}未检测到明显连贯性，识别为新段落: {line_text}")
                    
                        # 根据分段判断结果处理
                        if is_new_paragraph:
                            # 合并当前段落并开始新段落
                            if current_paragraph_lines:
                                paragraph_text = " ".join(current_paragraph_lines)
                                y_based_paragraphs.append(paragraph_text)
                                current_paragraph_lines = []
                        
                        # 添加当前行到段落
                        current_paragraph_lines.append(line_text)
                    
                    # 添加最后一个段落
                    if current_paragraph_lines:
                        paragraph_text = " ".join(current_paragraph_lines)
                        y_based_paragraphs.append(paragraph_text)
                
                # 输出基于Y坐标的段落分割结果
                if self.debug:
                    print(f"基于Y坐标分段得到{len(y_based_paragraphs)}个段落:")
                    for i, p in enumerate(y_based_paragraphs):
                        print(f"Y坐标段落{i+1}: {p}")
                
                # 使用Y坐标分段结果作为最终输出
                raw_text = "\n\n".join(y_based_paragraphs)
                
                # 简单清理文本，但保留段落结构
                return self.clean_text(raw_text)
            
            return ""
            
        except Exception as e:
            self.ocr_errors += 1
            if self.debug:
                print(f"OCR错误: {e}")
            import traceback
            traceback.print_exc()
            return ""

    @staticmethod
    def clean_text(text):
        """简单清理文本，保留段落格式"""
        if not text:
            return ""
        
        # 分割段落，分别清理每个段落
        paragraphs = text.split("\n\n")
        cleaned_paragraphs = []
        
        for paragraph in paragraphs:
            # 移除段落内多余的空白字符
            paragraph = " ".join(paragraph.split())
            
            # 常见OCR错误修正
            paragraph = paragraph.replace("|", "I")
            
            # 单词之间确保只有一个空格
            paragraph = " ".join(paragraph.split())
            
            # 添加到清理后的段落列表
            if paragraph.strip():  # 只添加非空段落
                cleaned_paragraphs.append(paragraph.strip())
        
        # 调试输出（默认关闭，避免影响性能）
        # print(f"清理后的段落数量: {len(cleaned_paragraphs)}")
        # for i, p in enumerate(cleaned_paragraphs):
        #     print(f"段落 {i+1}: {p}")
        
        # 合并清理后的段落，保留段落格式
        return "\n\n".join(cleaned_paragraphs)

    def reload_settings(self):
        """Reload OCR settings from config"""
        with self._lock:
            self.max_retries = config.get('OCR_TRANSLATION', 'MAX_RETRIES', 3)
            self.ocr_timeout = config.get('PADDLEOCR', 'OCR_TIMEOUT', 30)
            if PADDLEOCR_AVAILABLE:
                self._initialize_ocr() 
