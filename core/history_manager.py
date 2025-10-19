import os
import json
import datetime

class HistoryManager:
    def __init__(self, history_file_path):
        self.history_file = history_file_path
        self.translation_history = []
        self.load_history()

    def load_history(self):
        """从文件加载翻译历史记录"""
        try:
            # 确保历史目录存在
            history_dir = os.path.dirname(self.history_file)
            if not os.path.exists(history_dir):
                os.makedirs(history_dir)
            
            # 如果历史文件存在，加载它
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    self.translation_history = json.load(f)
                print(f"已加载 {len(self.translation_history)} 条翻译历史记录")
        except Exception as e:
            print(f"加载历史记录失败: {e}")
            self.translation_history = []

    def save_history(self):
        """保存翻译历史记录到文件"""
        try:
            # 确保历史目录存在
            history_dir = os.path.dirname(self.history_file)
            if not os.path.exists(history_dir):
                os.makedirs(history_dir)
            
            # 保存历史记录到文件
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.translation_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存历史记录失败: {e}")

    def add_to_history(self, source_text, translated_text, source_lang, target_lang):
        """添加翻译结果到历史记录"""
        # 创建历史记录条目
        history_item = {
            'time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'source_text': source_text,
            'translated_text': translated_text,
            'source_lang': source_lang,
            'target_lang': target_lang
        }
        
        # 添加到历史记录列表
        self.translation_history.append(history_item)
        
        # 限制历史记录最大条目数
        max_history = 100  # 最多保存100条记录
        if len(self.translation_history) > max_history:
            self.translation_history = self.translation_history[-max_history:]
        
        # 保存历史记录
        self.save_history()

    def add_translation(self, source_text, translated_text, source_lang, target_lang):
        """添加翻译结果到历史记录（add_to_history的别名）"""
        return self.add_to_history(source_text, translated_text, source_lang, target_lang)

    def get_history(self):
        """获取历史记录"""
        return self.translation_history 