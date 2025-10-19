# Ollama Translation API 文档

## 接口：`/translate`

该接口提供基于 Ollama 大语言模型的文本翻译服务，专为社交媒体内容优化，生成自然、口语化的翻译结果。

### 基本信息

- **URL**: `/translate`
- **方法**: POST
- **内容类型**: application/json
- **响应格式**: JSON

### 请求参数

| 参数名 | 类型 | 必填 | 默认值 | 描述 |
|--------|------|------|--------|------|
| source_lang | string | 否 | "auto" | 源语言代码，如 "English"、"Chinese"、"Japanese" 等 |
| target_lang | string | 否 | "en" | 目标语言代码，如 "English"、"Chinese"、"Japanese" 等 |
| text_list | array | 是 | - | 需要翻译的文本数组，每个元素为一个字符串 |
| placeholder_markers | array | 否 | null | 占位符标记数组，用于保护特殊内容（如表情符号）不被翻译 |

#### placeholder_markers 参数说明

该参数是一个包含2-3个元素的数组，用于定义如何处理特殊内容（主要是表情符号）：

- 第一个元素：左标记
- 第二个元素：右标记
- 第三个元素（可选）：标签标记

例如：`["{{", "}}"]` 或 `["<", ">", "tag"]`

### 请求示例

```json
{
  "source_lang": "English",
  "target_lang": "Chinese",
  "text_list": [
    "Hello world! 😊 How are you today?",
    "I love programming! It's so fun! 🚀"
  ],
  "placeholder_markers": ["{{", "}}"]
}
```

### 响应参数

| 参数名 | 类型 | 描述 |
|--------|------|------|
| translations | array | 翻译结果数组 |

#### translations 数组元素

| 参数名 | 类型 | 描述 |
|--------|------|------|
| detected_source_lang | string | 检测到的源语言（当前版本直接返回请求中的 source_lang） |
| text | string | 翻译后的文本 |

### 响应示例

```json
{
  "translations": [
    {
      "detected_source_lang": "English",
      "text": "你好，世界！😊 今天怎么样啊？"
    },
    {
      "detected_source_lang": "English",
      "text": "我超爱编程！太有趣了！🚀"
    }
  ]
}
```

### 错误响应

当发生错误时，API 将返回以下格式的响应，同时 HTTP 状态码为 500：

```json
{
  "error": "错误信息",
  "translations": [
    {
      "detected_source_lang": "auto",
      "text": "原始文本1"
    },
    {
      "detected_source_lang": "auto",
      "text": "原始文本2"
    }
  ]
}
```

### 特殊功能

1. **表情符号和特殊字符处理**：
   - 使用 `placeholder_markers` 参数可以保护表情符号和特殊字符在翻译过程中不被修改
   - API 会自动识别表情符号，用占位符替换，翻译后再恢复原内容

2. **社交媒体优化**：
   - 翻译结果针对社交媒体内容进行了优化，生成自然、口语化的翻译
   - 保留原文的情感和意图，使用目标语言中自然的表达方式
   - 保留原文中的 @提及、#标签 和表情符号

3. **失败处理**：
   - 如果翻译失败，API 会返回原始文本作为翻译结果

### 使用示例

#### Python 示例

```python
import requests
import json

url = "http://localhost:5000/translate"

payload = {
    "source_lang": "English",
    "target_lang": "Chinese",
    "text_list": ["Hello world! How are you today? 😊"],
    "placeholder_markers": ["{{", "}}"]
}

headers = {
    "Content-Type": "application/json"
}

response = requests.post(url, json=payload, headers=headers)
result = response.json()

print(json.dumps(result, indent=2, ensure_ascii=False))
```

#### JavaScript 示例

```javascript
const url = 'http://localhost:5000/translate';

const payload = {
  source_lang: 'English',
  target_lang: 'Chinese',
  text_list: ['Hello world! How are you today? 😊'],
  placeholder_markers: ['{{', '}}']
};

fetch(url, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(payload)
})
.then(response => response.json())
.then(data => console.log(JSON.stringify(data, null, 2)))
.catch(error => console.error('Error:', error));
```

### 注意事项

1. 当前使用的 Ollama 模型为 `gemma2:27b`
2. API 服务器默认运行在 `http://0.0.0.0:5000`
3. 翻译质量取决于底层 Ollama 模型的能力
4. 对于大量文本的翻译请求，可能需要较长的处理时间 