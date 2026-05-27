import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")


def get_current_date():
    now = datetime.now()
    return f"{now.month:02d}月{now.day:02d}"


EXTRACTION_PROMPT = """# Role：资深 ToB 产品运营 / 商业化产品经理

# Task：
请根据我提供的 PRD（产品需求文档）或功能描述，为我撰写一段用于对外发布的「产品功能更新卡片（Release Note）文案」。

# Guidelines (核心规则)：
1. **剥离底层技术细节**：严格过滤掉架构设计、具体代码实现、内部数据表、研发术语等纯技术实现细节。
2. **完全聚焦业务价值**：站在"客户视角"，用最精炼的语言说明：**开放了什么新能力？解决了客户什么业务痛点？带来了什么收益？**
3. **极致精炼（单段话原则）**：文案需要极度干练，拒绝长篇大论。将核心能力与价值浓缩在「一段话」内，适合作为卡片式日志直接阅读。
4. **统一语言风格**：专业、客观、有商业感，避免口语化，多用"全新推出"、"有效提升"、"优化升级"等积极正面的词汇。
5. **标题要吸引人**：不要简单的"xx上线"，要更有吸引力，比如"推荐场景扩展：购物车推荐能力上线"、"搜索体验升级：置顶物品搜索框优化"。

# 分类选项（选择一个）：
- 重点能力
- 通用能力
- 搜索能力
- 推荐能力
- 对话能力

# 输出格式要求：
直接返回 JSON 对象，不要使用 Markdown 代码块。
{
  "title": "功能名称（吸引人，不要太简单）",
  "content": "具体更新内容与业务价值，用一到两句话连贯表达，要有商业感",
  "category": "重点能力/通用能力/搜索能力/推荐能力/对话能力"
}

# 优秀示例（请学习这个风格）：
输入：大量关于购物车推荐的PRD
输出：
{
  "title": "推荐场景扩展：购物车推荐能力上线",
  "content": "在现有 “主页推荐” 与 “详情页推荐” 基础上，全新推出 “购物车推荐” 场景。支持客户在购物车中传入多个父商品，平台将基于各父商品独立召回并融合推荐结果，帮助电商客户有效提升客单价与整体收入。",
  "category": "推荐能力"
}

# 另一个优秀示例：
输入：关于搜索框优化的PRD
输出：
{
  "title": "搜索体验升级：置顶物品搜索框优化",
  "content": "统一所有推荐场景的「指定物品」搜索能力，搜索框置顶展示，支持按物品ID与名称模糊匹配，帮助运营人员快速定位目标物品，有效提升配置效率。",
  "category": "搜索能力"
}

# Input：
{{PRD_CONTENT}}
"""


def extract_with_claude(prd_content):
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise Exception("未配置 ANTHROPIC_API_KEY（云端请在 Streamlit Secrets 中配置，或切换 LLM_PROVIDER=deepseek）")

    prompt = EXTRACTION_PROMPT.replace("{{PRD_CONTENT}}", prd_content)

    headers = {
        "x-api-key": api_key,
        "content-type": "application/json",
        "anthropic-version": "2023-06-01"
    }

    payload = {
        "model": ANTHROPIC_MODEL,
        "max_tokens": 1024,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    try:
        base_url = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
        if base_url.endswith("/"):
            base_url = base_url[:-1]
        response = requests.post(
            f"{base_url}/v1/messages",
            headers=headers,
            json=payload,
            timeout=60
        )
        if response.status_code in (401, 403):
            raise Exception("Claude 鉴权失败(401/403)：请检查 Streamlit Secrets 中的 ANTHROPIC_API_KEY 是否正确、是否有额度/权限")
        response.raise_for_status()

        result = response.json()
        content_text = result["content"][0]["text"]

        json_match = content_text.find('{')
        if json_match > 0:
            content_text = content_text[json_match:]

        json_end = content_text.rfind('}')
        if json_end > 0:
            content_text = content_text[:json_end+1]

        extracted = json.loads(content_text)
        extracted["date"] = get_current_date()

        valid_categories = ["通用能力", "搜索能力", "推荐能力"]
        if extracted.get("category") not in valid_categories:
            extracted["category"] = "通用能力"

        return extracted
    except requests.exceptions.HTTPError as e:
        if response.status_code == 404:
            raise Exception(
                f"Claude 接口报错(404 Not Found)：当前请求地址为 {base_url}/v1/messages，"
                f"当前模型为 {ANTHROPIC_MODEL}。这通常表示模型 ID 不可用或账号无权访问该模型。"
            )
        response.raise_for_status()
    except Exception as e:
        print(f"Claude API 调用失败: {str(e)}")
        raise


def extract_with_deepseek(prd_content):
    api_key = os.getenv("DEEPSEEK_API_KEY")
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    if not api_key:
        raise Exception("未配置 DEEPSEEK_API_KEY（云端请在 Streamlit Secrets 中配置，或切换 LLM_PROVIDER=claude）")

    prompt = EXTRACTION_PROMPT.replace("{{PRD_CONTENT}}", prd_content)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.7,
        "max_tokens": 2000,
        "response_format": {"type": "json_object"}
    }

    try:
        response = requests.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        if response.status_code == 401:
            raise Exception("DeepSeek 鉴权失败(401)：请检查 Streamlit Secrets 中的 DEEPSEEK_API_KEY 是否正确，或切换 LLM_PROVIDER=claude")
        response.raise_for_status()

        result = response.json()
        extracted_json_str = result["choices"][0]["message"]["content"].strip()
        extracted = json.loads(extracted_json_str)

        extracted["date"] = get_current_date()

        valid_categories = ["通用能力", "搜索能力", "推荐能力"]
        if extracted.get("category") not in valid_categories:
            extracted["category"] = "通用能力"

        return extracted
    except Exception as e:
        print(f"DeepSeek API 调用失败: {str(e)}")
        raise


def extract_text_from_prd(prd_content):
    llm_provider = os.getenv("LLM_PROVIDER", "claude").lower()

    if llm_provider == "claude":
        print("使用 Claude 模型...")
        return extract_with_claude(prd_content)
    elif llm_provider == "deepseek":
        print("使用 DeepSeek 模型...")
        return extract_with_deepseek(prd_content)
    else:
        print(f"未知模型: {llm_provider}，默认使用 Claude")
        return extract_with_claude(prd_content)

def refine_text_with_ai(original_content, user_requirement):
    llm_provider = os.getenv("LLM_PROVIDER", "claude").lower()
    
    prompt = f"""# Role：资深 ToB 产品运营 / 商业化产品经理

# Task：
请根据用户的具体要求，对以下「产品功能更新卡片（Release Note）文案」进行二次润色和修改。

# 原文案：
{original_content}

# 用户要求：
{user_requirement}

# Guidelines (核心规则)：
1. 严格遵循用户的修改要求。
2. 保持专业、客观、有商业感的 ToB 产品发布语言风格。
3. 依然需要保持精炼，尽量用一到两句话连贯表达。
4. 直接输出修改后的文案内容，不要包含任何前缀、解释、Markdown 标记或多余的话语。

# 修改后的文案："""

    if llm_provider == "deepseek":
        api_key = os.getenv("DEEPSEEK_API_KEY")
        base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        if not api_key:
            raise Exception("未配置 DEEPSEEK_API_KEY（云端请在 Streamlit Secrets 中配置，或切换 LLM_PROVIDER=claude）")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        payload = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 1000
        }
        response = requests.post(f"{base_url}/chat/completions", headers=headers, json=payload, timeout=60)
        if response.status_code == 401:
            raise Exception("DeepSeek 鉴权失败(401)：请检查 Streamlit Secrets 中的 DEEPSEEK_API_KEY 是否正确，或切换 LLM_PROVIDER=claude")
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
        
    else:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise Exception("请先在 .env 文件中配置 ANTHROPIC_API_KEY")
        headers = {
            "x-api-key": api_key,
            "content-type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        payload = {
            "model": ANTHROPIC_MODEL,
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}]
        }
        base_url = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
        if base_url.endswith("/"):
            base_url = base_url[:-1]
        response = requests.post(f"{base_url}/v1/messages", headers=headers, json=payload, timeout=60)
        if response.status_code == 404:
            raise Exception(
                f"Claude 接口报错(404 Not Found)：当前请求地址为 {base_url}/v1/messages，"
                f"当前模型为 {ANTHROPIC_MODEL}。这通常表示模型 ID 不可用或账号无权访问该模型。"
            )
        response.raise_for_status()
        return response.json()["content"][0]["text"].strip()

def translate_to_english(text):
    llm_provider = os.getenv("LLM_PROVIDER", "claude").lower()
    
    prompt = f"""# Role: Professional B2B Product Marketing Manager / Translator

# Task:
Translate the following Chinese Release Note into professional, business-oriented English. 
Keep it concise, engaging, and suitable for an enterprise software update log.
Do NOT output any explanations or markdown, just the translated text.

# Chinese Text:
{text}

# English Translation:"""

    if llm_provider == "deepseek":
        api_key = os.getenv("DEEPSEEK_API_KEY")
        base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        payload = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 1000
        }
        response = requests.post(f"{base_url}/chat/completions", headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
        
    else:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise Exception("请先在 .env 文件中配置 ANTHROPIC_API_KEY")
        headers = {
            "x-api-key": api_key,
            "content-type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        payload = {
            "model": ANTHROPIC_MODEL,
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}]
        }
        base_url = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
        if base_url.endswith("/"):
            base_url = base_url[:-1]
        response = requests.post(f"{base_url}/v1/messages", headers=headers, json=payload, timeout=60)
        if response.status_code == 404:
            raise Exception(
                f"Claude 接口报错(404 Not Found)：当前请求地址为 {base_url}/v1/messages，"
                f"当前模型为 {ANTHROPIC_MODEL}。这通常表示模型 ID 不可用或账号无权访问该模型。"
            )
        response.raise_for_status()
        return response.json()["content"][0]["text"].strip()
