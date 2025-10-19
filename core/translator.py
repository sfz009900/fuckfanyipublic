import os
import json
from collections import OrderedDict
import requests
import translators as ts
from config_manager import config
from utils.logger import get_logger

logger = get_logger(__name__)

class Translator:
    def __init__(self):
        self.source_lang = config.SOURCE_LANGUAGE
        self.target_lang = config.TARGET_LANGUAGE
        self.api_url = config.API_URL
        self.translation_errors = 0
        # Use [CACHE] section for retry/cache limits
        self.max_retries = config.get('CACHE', 'MAX_RETRIES', 3)
        self.max_cache_size = config.get('CACHE', 'MAX_CACHE_SIZE', 1000)
        # Persistent cache
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self._cache_dir = os.path.join(project_root, 'cache')
        os.makedirs(self._cache_dir, exist_ok=True)
        self._cache_file = os.path.join(self._cache_dir, 'translation_cache.json')
        # Ordered cache for simple LRU behavior
        self.translation_cache = OrderedDict()
        self._load_cache()
        self.translation_engine = config.get('OCR_TRANSLATION', 'TRANSLATION_ENGINE', 'default')
        self.translation_prompt = config.get('OCR_TRANSLATION', 'TRANSLATION_PROMPT', '')
        self.translation_model = config.get('OCR_TRANSLATION', 'TRANSLATION_MODEL', 'llama2')
        # Add OpenAI specific configurations
        # Prefer config, fallback to environment
        self.openai_api_key = config.get('OCR_TRANSLATION', 'OPENAI_API_KEY', '') or os.getenv('OPENAI_API_KEY', '')
        self.openai_model = config.get('OCR_TRANSLATION', 'OPENAI_MODEL', 'gpt-3.5-turbo')

    def _cache_key(self, text: str) -> str:
        """Build a stable cache key for a translation input."""
        engine = str(self.translation_engine or '').lower()
        model = str(self.translation_model or '')
        return f"{engine}|{model}|{self.source_lang}|{self.target_lang}|{text}"

    def _load_cache(self) -> None:
        try:
            if os.path.exists(self._cache_file):
                with open(self._cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        # Preserve order when loading
                        self.translation_cache = OrderedDict(data)
                        # Trim if oversized
                        while len(self.translation_cache) > self.max_cache_size:
                            self.translation_cache.popitem(last=False)
        except Exception as e:
            logger.warning(f"加载翻译缓存失败: {e}")

    def _save_cache(self) -> None:
        try:
            with open(self._cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.translation_cache, f, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"保存翻译缓存失败: {e}")

    def translate_text(self, text):
        """Send the text to the translation API"""
        try:
            # Clean the text to remove or escape problematic characters
            cleaned_text = text.replace('\\', '\\\\')  # Escape backslashes
            
            # Check translation cache (persistent LRU)
            cache_key = self._cache_key(cleaned_text)
            if cache_key in self.translation_cache:
                # Move to MRU position
                self.translation_cache.move_to_end(cache_key, last=True)
                logger.info("Using cached translation")
                return self.translation_cache[cache_key]
            
            if self.translation_engine.lower() == "ollama":
                return self._translate_with_ollama(cleaned_text)
            elif self.translation_engine.lower() == "openai":
                return self._translate_with_openai(cleaned_text)
            elif self.translation_engine == "谷歌翻译":
                return self._translate_with_google(cleaned_text)
            elif self.translation_engine == "测试服务器1":
                return self._translate_with_test_server(cleaned_text)
            elif self.translation_engine == "微软翻译":
                return self._translate_with_microsoft(cleaned_text)
            elif self.translation_engine == "可腾翻译":
                return self._translate_with_kerten(cleaned_text)
            else:
                try:
                    translated_text = ts.translate_text(
                        query_text=cleaned_text,
                        translator=self.translation_engine.lower(),
                        from_language=self.source_lang,
                        to_language=self.target_lang
                    )
                    if translated_text:
                        self._update_cache(cache_key, translated_text)
                        return translated_text
                    return None
                except Exception as e:
                    print(f"Error during translators library translation: {e}")
                    return None
        
        except Exception as e:
            self.translation_errors += 1
            print(f"Error during translation API call: {e}")
            return None

    def reload_settings(self):
        """Reload translation settings from config"""
        self.source_lang = config.SOURCE_LANGUAGE
        self.target_lang = config.TARGET_LANGUAGE
        self.api_url = config.API_URL
        self.max_retries = config.get('CACHE', 'MAX_RETRIES', 3)
        self.max_cache_size = config.get('CACHE', 'MAX_CACHE_SIZE', 1000)
        self.translation_engine = config.get('OCR_TRANSLATION', 'TRANSLATION_ENGINE', 'default')
        self.translation_prompt = config.get('OCR_TRANSLATION', 'TRANSLATION_PROMPT', '')
        self.translation_model = config.get('OCR_TRANSLATION', 'TRANSLATION_MODEL', 'llama2')
        self.openai_api_key = config.get('OCR_TRANSLATION', 'OPENAI_API_KEY', '')
        self.openai_model = config.get('OCR_TRANSLATION', 'OPENAI_MODEL', 'gpt-3.5-turbo')
        # Trim cache if size reduced
        while len(self.translation_cache) > self.max_cache_size:
            try:
                self.translation_cache.popitem(last=False)
            except Exception:
                break

    def _translate_with_ollama(self, text):
        """Translate text using Ollama API"""
        try:
            # Format the prompt according to the template
            prompt = self.translation_prompt.format(
                source_lang=self.source_lang,
                target_lang=self.target_lang,
                text=text
            )
            
            payload = {
                "model": self.translation_model,
                "prompt": prompt,
                "stream": False
            }
            
            headers = {
                "Content-Type": "application/json"
            }
            
            print("\n发送Ollama API请求...")
            print(f"请求URL: {self.api_url}/api/generate")
            print(f"请求payload: {payload}")

            # Append "/api/generate" to the API URL for Ollama
            ollama_api_url = f"{self.api_url}/api/generate"

            try:
                response = requests.post(ollama_api_url, json=payload, headers=headers, timeout=30)
                print(f"API响应状态码: {response.status_code}")

                if response.status_code != 200:
                    print(f"HTTP错误: {response.status_code}")
                    print(f"响应内容: {response.text}")
                    return None

                result = response.json()
                print(f"API响应内容: {result}")

                if "response" in result:
                    translated_text = result["response"]
                    cache_key = self._cache_key(text)
                    self._update_cache(cache_key, translated_text)
                    return translated_text
                else:
                    print("Ollama translation failed or returned empty result.")
                    return None

            except requests.exceptions.RequestException as req_e:
                print(f"网络请求错误: {req_e}")
                return None
            except ValueError as json_e:
                print(f"JSON解析错误: {json_e}")
                print(f"原始响应: {response.text if 'response' in locals() else 'No response'}")
                return None

        except Exception as e:
            print(f"Error during Ollama translation: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _translate_with_openai(self, text):
        """Translate text using OpenAI API"""
        try:
            if not self.openai_api_key:
                print("OpenAI API key not configured")
                return None

            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }
            
            # Format the system message for translation
            system_message = ""
            
            # Format the prompt according to the template
            prompt = self.translation_prompt.format(
                source_lang=self.source_lang,
                target_lang=self.target_lang,
            )
            
            print(f"\nPrompt template: {prompt}")
            
            payload = {
                "model": self.openai_model,
                "messages": [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": text}
                ],
                "temperature": config.get('OCR_TRANSLATION', 'temperature', 0.3)  # Use temperature from config
            }
            
            response = requests.post(
                f"{self.api_url}/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            result = response.json()
            
            if "choices" in result and len(result["choices"]) > 0:
                translated_text = result["choices"][0]["message"]["content"].strip()
                cache_key = self._cache_key(text)
                self._update_cache(cache_key, translated_text)
                return translated_text
            else:
                print("OpenAI translation failed or returned empty result.")
                return None
                
        except Exception as e:
            print(f"Error during OpenAI translation: {e}")
            return None

    def _translate_with_default_api(self, text):
        """Translate text using the default API"""
        payload = {
            "source_lang": self.source_lang,
            "target_lang": self.target_lang,
            "text_list": [text],
            "placeholder_markers": None
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        print("\n发送API请求...")
        response = requests.post(self.api_url, json=payload, headers=headers, timeout=30)
        print(f"API响应状态码: {response.status_code}")
        
        result = response.json()
        print(f"API响应内容: {result}")
        
        # 检查是否有错误
        if "error" in result:
            print(f"API返回错误: {result['error']}")
            # 如果API返回了错误，但仍然提供了翻译结果，使用它
            if "translations" in result and len(result["translations"]) > 0:
                translated_text = result["translations"][0]["text"]
                cache_key = f"{text}_{self.source_lang}_{self.target_lang}"
                self._update_cache(cache_key, translated_text)
                return translated_text
            return None
        
        if "translations" in result and len(result["translations"]) > 0:
            translated_text = result["translations"][0]["text"]
            cache_key = self._cache_key(text)
            self._update_cache(cache_key, translated_text)
            return translated_text
        else:
            print("Translation failed or returned empty result.")
            return None

    def _update_cache(self, cache_key, translated_text):
        """Update the LRU translation cache and persist to disk."""
        self.translation_cache[cache_key] = translated_text
        # Move to MRU
        try:
            self.translation_cache.move_to_end(cache_key, last=True)
        except Exception:
            # If underlying type changed, ignore
            pass
        # Trim cache if too large
        while len(self.translation_cache) > self.max_cache_size:
            try:
                self.translation_cache.popitem(last=False)
            except Exception:
                # Fallback: pop first key
                self.translation_cache.pop(next(iter(self.translation_cache)))
                break
        # Persist
        self._save_cache()

    def _translate_with_test_server(self, text):
        """Translate text using test server API"""
        try:
            scene = config.get('OCR_TRANSLATION', 'scene', 1)  # Get scene from config
            
            payload = {
                "source_lang": self.source_lang,
                "target_lang": self.target_lang,
                "text_list": [text],
                "placeholder_markers": None,
                "scene": scene
            }
            
            headers = {
                "Content-Type": "application/json"
            }
            
            print("\n发送测试服务器API请求...")
            response = requests.post(
                "https://ollama-cjsfy-git-testpublic-sfz009900s-projects.vercel.app/translate",
                json=payload,
                headers=headers,
                timeout=60  # 添加30秒超时设置
            )
            print(f"API响应状态码: {response.status_code}")
            
            result = response.json()
            print(f"API响应内容: {result}")
            
            if "translations" in result and len(result["translations"]) > 0:
                translated_text = result["translations"][0]["text"]
                cache_key = self._cache_key(text)
                self._update_cache(cache_key, translated_text)
                return translated_text
            else:
                print("Translation failed or returned empty result.")
                return None
                
        except Exception as e:
            print(f"Error during test server translation: {e}")
            return None

    def _translate_with_google(self, text):
        """Translate text using Google Translate API"""
        try:
            base_url = "http://translate.google.com/translate_a/single"
            params = {
                "client": "gtx",
                "dt": "t",
                "dj": "1",
                "ie": "UTF-8",
                "sl": self.source_lang,
                "tl": self.target_lang,
                "q": text
            }
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            
            print("\n发送Google翻译API请求...")
            response = requests.get(base_url, params=params, headers=headers, timeout=15)
            print(f"API响应状态码: {response.status_code}")
            
            result = response.json()
            print(f"API响应内容: {result}")
            
            if "sentences" in result and len(result["sentences"]) > 0:
                translated_text = result["sentences"][0]["trans"]
                cache_key = self._cache_key(text)
                self._update_cache(cache_key, translated_text)
                return translated_text
            else:
                print("Google translation failed or returned empty result.")
                return None
                
        except Exception as e:
            print(f"Error during Google translation: {e}")
            return None

    def _translate_with_microsoft(self, text):
        """Translate text using Microsoft Translator API"""
        try:
            base_url = "api.microsofttranslator.com/v2/Http.svc/Translate"
            params = {
                "appId": "AFC76A66CF4F434ED080D245C30CF1E71C22959C",
                "from": self.source_lang,
                "to": self.target_lang,
                "text": text
            }
            
            print("\n发送Microsoft翻译API请求...")
            response = requests.get(f"http://{base_url}", params=params, timeout=30)
            print(f"API响应状态码: {response.status_code}")
            
            result = response.text
            print(f"API响应内容: {result}")
            
            # Extract the translated text from XML response
            # Response format: <string xmlns="http://schemas.microsoft.com/2003/10/Serialization/">translated_text</string>
            if result and "</string>" in result:
                translated_text = result.split(">")[1].split("<")[0]
                cache_key = self._cache_key(text)
                self._update_cache(cache_key, translated_text)
                return translated_text
            else:
                print("Microsoft translation failed or returned empty result.")
                return None
                
        except Exception as e:
            print(f"Error during Microsoft translation: {e}")
            return None

    def _translate_with_kerten(self, text):
        """Translate text using Kerten Translation API"""
        try:
            base_url = "api.kertennet.com/live/translate"
            params = {
                "text": text,
                "to": self.target_lang
            }
            
            print("\n发送可腾翻译API请求...")
            response = requests.get(f"http://{base_url}", params=params, timeout=30)
            print(f"API响应状态码: {response.status_code}")
            
            result = response.json()
            print(f"API响应内容: {result}")
            
            if result.get("code") == 200 and "data" in result:
                translated_text = result["data"]["target"]
                cache_key = self._cache_key(text)
                self._update_cache(cache_key, translated_text)
                return translated_text
            else:
                print("Kerten translation failed or returned empty result.")
                return None
                
        except Exception as e:
            print(f"Error during Kerten translation: {e}")
            return None

    @staticmethod
    def _detect_language(text: str) -> str:
        """Lightweight language detection for common cases.

        Returns codes: 'zh', 'en', 'ja', 'ko', 'ru', 'fr', 'de', 'es'.
        Defaults to 'en' if uncertain.
        """
        if not text:
            return 'en'
        import re
        counts = {}
        counts['zh'] = len(re.findall(r"[\u4e00-\u9fff]", text))
        counts['ja'] = len(re.findall(r"[\u3040-\u30ff]", text))
        counts['ko'] = len(re.findall(r"[\uac00-\ud7af]", text))
        counts['ru'] = len(re.findall(r"[\u0400-\u04FF]", text))
        counts['en'] = len(re.findall(r"[A-Za-z]", text))
        total = sum(counts.values()) or 1
        lang = max(counts, key=counts.get)
        # Low confidence -> default to en
        if counts[lang] / total < 0.35:
            return 'en'
        return lang

    def translate(self, text):
        """Translate text from source_lang to target_lang
        
        Args:
            text (str): The text to translate
            
        Returns:
            dict: Translation result with keys:
                - translated_text (str): The translated text
                - source_lang (str): The source language
                - target_lang (str): The target language
        """
        try:
            if not text or not text.strip():
                return None

            # Auto-detect source language if configured
            original_source = self.source_lang
            effective_source = original_source
            if str(original_source).lower() in {"auto", "detect", ""}:
                effective_source = self._detect_language(text)
            # Temporarily apply detected source for this translation
            self.source_lang = effective_source
            
            # 检查是否含有多个段落
            has_paragraphs = "\n\n" in text
            
            if has_paragraphs:
                # 处理多段落文本
                print("检测到多段落文本，分段处理翻译...")
                paragraphs = text.split("\n\n")
                translated_paragraphs = []
                
                for i, paragraph in enumerate(paragraphs):
                    print(f"翻译段落 {i+1}/{len(paragraphs)}: {paragraph[:50]}...")
                    translated_para = self.translate_text(paragraph)
                    if translated_para:
                        translated_paragraphs.append(translated_para)
                    else:
                        # 如果翻译失败，保留原文
                        translated_paragraphs.append(paragraph)
                
                # 合并翻译后的段落，保留原始格式
                translated_text = "\n\n".join(translated_paragraphs)
            else:
                # 处理单段落文本
                translated_text = self.translate_text(text)
            
            if not translated_text:
                print("翻译失败")
                # restore before return
                self.source_lang = original_source
                return None
            
            # 返回翻译结果
            result = {
                'translated_text': translated_text,
                'source_lang': self.source_lang,
                'target_lang': self.target_lang
            }
            # restore original setting
            self.source_lang = original_source
            return result
        except Exception as e:
            self.translation_errors += 1
            print(f"翻译过程中发生错误: {str(e)}")
            import traceback
            traceback.print_exc()
            # ensure restore
            try:
                self.source_lang = original_source
            except Exception:
                pass
            return None
