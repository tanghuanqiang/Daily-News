import dashscope
import requests
import re
from typing import Optional, Dict
from database import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize DashScope API
dashscope.api_key = settings.DASHSCOPE_API_KEY

# Initialize OpenAI client for NVIDIA API (if needed)
_nvidia_client = None

def get_nvidia_client():
    """Get or create NVIDIA OpenAI client"""
    global _nvidia_client
    if _nvidia_client is None and settings.NVIDIA_API_KEY:
        try:
            from openai import OpenAI
            _nvidia_client = OpenAI(
                base_url="https://integrate.api.nvidia.com/v1",
                api_key=settings.NVIDIA_API_KEY
            )
        except ImportError:
            logger.error("OpenAI library not installed. Please run: pip install openai")
            return None
    return _nvidia_client


class NewsSummarizer:
    """Generate news summaries using Alibaba Qwen LLM or Local Ollama"""
    
    def __init__(self):
        self.provider = settings.LLM_PROVIDER
        if self.provider == "ollama":
            self.model = settings.OLLAMA_MODEL
            self.base_url = settings.OLLAMA_BASE_URL.rstrip('/')
            self.api_url = f"{self.base_url}/api/chat"
            # 初始化时检查连接
            self._check_ollama_connection()
        elif self.provider == "nvidia":
            self.model = settings.NVIDIA_MODEL
            # 检查NVIDIA API key
            if not settings.NVIDIA_API_KEY or settings.NVIDIA_API_KEY == "":
                logger.warning("NVIDIA API key not configured")
            else:
                client = get_nvidia_client()
                if client:
                    logger.info(f"NVIDIA GLM API initialized, model: {self.model}")
                else:
                    logger.error("Failed to initialize NVIDIA client")
        else:
            self.model = "qwen-turbo"  # Low-cost model, can upgrade to "qwen-plus"
    
    def _check_ollama_connection(self):
        """检查Ollama服务是否可用"""
        try:
            # 检查Ollama服务是否运行
            health_url = f"{self.base_url}/api/tags"
            response = requests.get(health_url, timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m.get("name", "") for m in models]
                if self.model not in model_names:
                    logger.warning(
                        f"Ollama模型 '{self.model}' 未找到。可用模型: {', '.join(model_names)}"
                    )
                else:
                    logger.info(f"Ollama连接正常，使用模型: {self.model}")
            else:
                logger.warning(f"Ollama服务响应异常: HTTP {response.status_code}")
        except requests.exceptions.ConnectionError:
            logger.error(
                f"无法连接到Ollama服务 ({self.base_url})。"
                f"请确保Ollama正在运行: ollama serve"
            )
        except requests.exceptions.Timeout:
            logger.error(f"连接Ollama服务超时 ({self.base_url})")
        except Exception as e:
            logger.warning(f"检查Ollama连接时出错: {str(e)}")
    
    def generate_summary(
        self, 
        title: str, 
        content: str, 
        roast_mode: bool = False,
        topic: Optional[str] = None
    ) -> str:
        """
        Generate a concise 1-2 sentence summary of news article
        
        Args:
            title: News title
            content: News content/description
            roast_mode: If True, generate humorous/roast-style summary
            topic: News topic/category (legacy parameter, not used after RAG removal)
        
        Returns:
            Summary string
        """
        # Generate summary using selected provider
        if self.provider == "dashscope":
            summary = self._generate_dashscope(title, content, roast_mode, topic)
        elif self.provider == "ollama":
            summary = self._generate_ollama(title, content, roast_mode, topic)
        elif self.provider == "nvidia":
            summary = self._generate_nvidia(title, content, roast_mode, topic)
        else:
            logger.warning(f"Unknown LLM provider: {self.provider}, using fallback")
            summary = self._fallback_summary(title, content, roast_mode)
        
        # Post-process summary to ensure format compliance
        return self._post_process_summary(summary, roast_mode)

    def _generate_ollama(self, title: str, content: str, roast_mode: bool, topic: Optional[str] = None) -> str:
        """Generate summary using local Ollama model"""
        try:
            prompt = self._build_prompt(title, content, roast_mode, topic)
            
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "stream": False,
                "temperature": 0.8 if roast_mode else 0.3,
            }
            
            response = requests.post(self.api_url, json=payload, timeout=120)
            
            if response.status_code == 200:
                result = response.json()
                if "message" in result and "content" in result["message"]:
                    summary = result["message"]["content"].strip()
                    logger.info(f"Generated summary (Ollama) for: {title[:50]}...")
                    return summary
                elif "choices" in result and len(result["choices"]) > 0:
                    # Fallback to OpenAI-compatible format if available
                    summary = result["choices"][0]["message"]["content"].strip()
                    logger.info(f"Generated summary (Ollama OpenAI-compat) for: {title[:50]}...")
                    return summary
                else:
                    logger.error(f"Ollama响应格式异常: {result}")
                    return self._fallback_summary(title, content, roast_mode)
            else:
                error_msg = f"Ollama API错误: HTTP {response.status_code}"
                try:
                    error_detail = response.json()
                    error_msg += f" - {error_detail}"
                except:
                    error_msg += f" - {response.text[:200]}"
                logger.error(error_msg)
                return self._fallback_summary(title, content, roast_mode)
            
        except requests.exceptions.ConnectionError as e:
            logger.error(
                f"无法连接到Ollama服务 ({self.api_url})。"
                f"请确保Ollama正在运行: ollama serve"
            )
            return self._fallback_summary(title, content, roast_mode)
        except requests.exceptions.Timeout:
            logger.error(f"Ollama请求超时 (超过120秒)，使用备用摘要")
            return self._fallback_summary(title, content, roast_mode)
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama请求异常: {str(e)}")
            return self._fallback_summary(title, content, roast_mode)
        except Exception as e:
            logger.error(f"Ollama摘要生成错误: {str(e)}", exc_info=True)
            return self._fallback_summary(title, content, roast_mode)

    def _generate_nvidia(self, title: str, content: str, roast_mode: bool, topic: Optional[str] = None) -> str:
        """Generate summary using NVIDIA GLM API"""
        if not settings.NVIDIA_API_KEY or settings.NVIDIA_API_KEY == "":
            logger.warning("NVIDIA API key not configured, using fallback summary")
            return self._fallback_summary(title, content, roast_mode)
        
        try:
            client = get_nvidia_client()
            if not client:
                logger.error("NVIDIA client not available")
                return self._fallback_summary(title, content, roast_mode)
            
            # 构建系统提示词和用户提示词
            if roast_mode:
                system_prompt = "你是一个顶级脱口秀演员，擅长用幽默吐槽总结新闻。只输出吐槽内容，不要任何解释。"
                user_prompt = f"""任务：用1句话吐槽这条新闻
要求：
- 抓住最离谱/最搞笑的槽点
- 使用网络流行语
- 不超过30字
- 只输出吐槽内容，不要任何解释、说明或元信息

新闻标题：{title}
新闻内容：{content}"""
            else:
                system_prompt = "你是一个专业新闻编辑，擅长写一句话摘要。只输出摘要，不要其他文字。"
                user_prompt = f"""任务：用1句话总结新闻核心
要求：
- 客观中性，不带倾向
- 抓住5W1H（谁、做了什么、结果）
- 不超过25字
- 只输出摘要，不要其他文字

新闻标题：{title}
新闻内容：{content}"""
            
            # 调用NVIDIA API
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.8 if roast_mode else 0.3,
                max_tokens=800,  # 增加到800，避免截断
                stream=False
            )
            
            # 提取摘要
            if response.choices and len(response.choices) > 0:
                message = response.choices[0].message
                
                # Try content field first
                summary = None
                if message and message.content:
                    summary = message.content.strip()
                
                # If content is empty, try reasoning_content (GLM reasoning mode)
                if not summary and hasattr(message, 'reasoning_content') and message.reasoning_content:
                    summary = message.reasoning_content.strip()
                    logger.debug("Using reasoning_content from NVIDIA GLM")
                
                # If we got a summary, process it with post-processor
                if summary:
                    logger.info(f"Generated summary (NVIDIA GLM) for: {title[:50]}...")
                    return summary
                
                # No content found, log warning and use fallback
                finish_reason = response.choices[0].finish_reason if hasattr(response.choices[0], 'finish_reason') else 'unknown'
                logger.warning(f"NVIDIA API returned no content. Finish reason: {finish_reason}")
                return self._fallback_summary(title, content, roast_mode)
            else:
                logger.error("NVIDIA API returned empty choices")
                return self._fallback_summary(title, content, roast_mode)
                
        except Exception as e:
            logger.error(f"NVIDIA GLM API error: {str(e)}", exc_info=True)
            return self._fallback_summary(title, content, roast_mode)
    
    def _generate_dashscope(self, title: str, content: str, roast_mode: bool, topic: Optional[str] = None) -> str:
        """Generate summary using DashScope (Alibaba Cloud)"""
        if not settings.DASHSCOPE_API_KEY or settings.DASHSCOPE_API_KEY == "":
            logger.warning("DashScope API key not configured, using fallback summary")
            return self._fallback_summary(title, content, roast_mode)
        
        try:
            prompt = self._build_prompt(title, content, roast_mode)
            
            response = dashscope.Generation.call(
                model=self.model,
                prompt=prompt,
                max_tokens=150,
                temperature=0.8 if roast_mode else 0.3,
                top_p=0.9
            )
            
            if response.status_code == 200:
                summary = response.output.text.strip()
                logger.info(f"Generated summary (DashScope) for: {title[:50]}...")
                return summary
            else:
                logger.error(f"DashScope API error: {response.message}")
                return self._fallback_summary(title, content, roast_mode)
                
        except Exception as e:
            logger.error(f"Summary generation error: {str(e)}")
            return self._fallback_summary(title, content, roast_mode)
    
    def _build_prompt(self, title: str, content: str, roast_mode: bool, topic: Optional[str] = None) -> str:
        """Build prompt for LLM based on mode"""
        if roast_mode:
            return f"""任务：用1句话吐槽这条新闻

要求（必须遵守）：
1. 只输出吐槽内容，不要任何解释、说明或元信息
2. 不要输出"分析请求"、"角色"、"任务"、"要求"等标题
3. 不要输出编号列表（如1. 2. 3.）
4. 不要输出markdown格式（如**粗体**、##标题）
5. 只输出纯文本吐槽
6. 抓住最离谱/最搞笑的槽点
7. 使用网络流行语
8. 不超过30字

新闻标题：{title}
新闻内容：{content}

吐槽："""
        else:
            return f"""你是一个专业新闻编辑，擅长写一句话摘要。

任务：用1句话总结新闻核心
要求：
- 客观中性，不带倾向
- 抓住5W1H（谁、做了什么、结果）
- 不超过25字
- 只输出摘要，不要其他文字

新闻标题：{title}
新闻内容：{content}

摘要："""
    
    def evaluate_relevance(self, topic: str, title: str, content: str) -> float:
        """
        评估新闻与主题的相关性分数 (0-1)
        
        Args:
            topic: 主题名称
            title: 新闻标题
            content: 新闻内容
            
        Returns:
            float: 相关性分数 (0-1)，默认0.5
        """
        try:
            if self.provider == "nvidia":
                return self._evaluate_relevance_nvidia(topic, title, content)
            elif self.provider == "ollama":
                return self._evaluate_relevance_ollama(topic, title, content)
            elif self.provider == "dashscope":
                return self._evaluate_relevance_dashscope(topic, title, content)
            else:
                logger.warning(f"Unknown LLM provider for relevance evaluation: {self.provider}")
                return 0.5  # 默认分数
        except Exception as e:
            logger.error(f"Error evaluating relevance: {str(e)}", exc_info=True)
            return 0.5  # 出错时返回默认分数
    
    def _evaluate_relevance_nvidia(self, topic: str, title: str, content: str) -> float:
        """使用NVIDIA GLM API评估相关性"""
        if not settings.NVIDIA_API_KEY or settings.NVIDIA_API_KEY == "":
            return 0.5
        
        try:
            client = get_nvidia_client()
            if not client:
                return 0.5
            
            system_prompt = "你是一个专业的新闻相关性评估助手，擅长评估新闻与主题的相关性。"
            user_prompt = f"""主题：{topic}

新闻标题：{title}

新闻内容：{content[:500]}

请评估这条新闻与主题"{topic}"的相关性，给出0-1之间的分数：
- 0.9-1.0: 高度相关，核心内容完全匹配主题
- 0.7-0.9: 较为相关，主要内容与主题相关
- 0.5-0.7: 中等相关，部分内容与主题相关
- 0.3-0.5: 低相关性，只有少量内容与主题相关
- 0.0-0.3: 几乎不相关

请只返回一个0-1之间的数字，例如：0.85"""
            
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=50,
                stream=False
            )
            
            if response.choices and len(response.choices) > 0:
                message = response.choices[0].message
                content_text = message.content if message.content else ""
                if hasattr(message, 'reasoning_content') and message.reasoning_content:
                    content_text = message.reasoning_content
                
                # 提取数字
                score_match = re.search(r'0?\.?\d+', content_text.strip())
                if score_match:
                    score = float(score_match.group())
                    # 限制在0-1之间
                    score = max(0.0, min(1.0, score))
                    logger.debug(f"Relevance score for '{title[:30]}...' with topic '{topic}': {score}")
                    return score
                else:
                    logger.warning(f"Could not parse relevance score from: {content_text}")
                    return 0.5
            else:
                return 0.5
                
        except Exception as e:
            logger.error(f"Error evaluating relevance with NVIDIA: {str(e)}")
            return 0.5
    
    def _evaluate_relevance_ollama(self, topic: str, title: str, content: str) -> float:
        """使用Ollama评估相关性"""
        try:
            prompt = f"""主题：{topic}

新闻标题：{title}

新闻内容：{content[:500]}

请评估这条新闻与主题"{topic}"的相关性，给出0-1之间的分数（0完全不相关，1完全相关）。
只返回一个数字，例如：0.85"""
            
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "stream": False,
                "temperature": 0.3,
            }
            
            response = requests.post(self.api_url, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                content_text = ""
                if "message" in result and "content" in result["message"]:
                    content_text = result["message"]["content"].strip()
                elif "choices" in result and len(result["choices"]) > 0:
                    content_text = result["choices"][0]["message"]["content"].strip()
                
                # 提取数字
                score_match = re.search(r'0?\.?\d+', content_text.strip())
                if score_match:
                    score = float(score_match.group())
                    score = max(0.0, min(1.0, score))
                    logger.debug(f"Relevance score (Ollama) for '{title[:30]}...' with topic '{topic}': {score}")
                    return score
                else:
                    logger.warning(f"Could not parse relevance score from Ollama response: {content_text}")
                    return 0.5
            else:
                return 0.5
                
        except Exception as e:
            logger.error(f"Error evaluating relevance with Ollama: {str(e)}")
            return 0.5
    
    def _evaluate_relevance_dashscope(self, topic: str, title: str, content: str) -> float:
        """使用DashScope评估相关性"""
        if not settings.DASHSCOPE_API_KEY or settings.DASHSCOPE_API_KEY == "":
            return 0.5
        
        try:
            prompt = f"""主题：{topic}

新闻标题：{title}

新闻内容：{content[:500]}

请评估这条新闻与主题"{topic}"的相关性，给出0-1之间的分数（0完全不相关，1完全相关）。
只返回一个数字，例如：0.85"""
            
            response = dashscope.Generation.call(
                model=self.model,
                prompt=prompt,
                max_tokens=50,
                temperature=0.3,
                top_p=0.9
            )
            
            if response.status_code == 200:
                content_text = response.output.text.strip()
                # 提取数字
                score_match = re.search(r'0?\.?\d+', content_text.strip())
                if score_match:
                    score = float(score_match.group())
                    score = max(0.0, min(1.0, score))
                    logger.debug(f"Relevance score (DashScope) for '{title[:30]}...' with topic '{topic}': {score}")
                    return score
                else:
                    logger.warning(f"Could not parse relevance score from DashScope response: {content_text}")
                    return 0.5
            else:
                return 0.5
                
        except Exception as e:
            logger.error(f"Error evaluating relevance with DashScope: {str(e)}")
            return 0.5
    
    def _fallback_summary(self, title: str, content: str, roast_mode: bool) -> str:
        """Fallback summary when API is not available"""
        # Simple truncation as fallback
        if content and len(content) > 100:
            summary = content[:100] + "..."
        elif content:
            summary = content
        else:
            summary = title
        
        if roast_mode:
            return f"📰 {summary} （AI摘要暂时不可用）"
        else:
            return summary
    
    def _post_process_summary(self, summary: str, roast_mode: bool) -> str:
        """
        Post-process summary to ensure format compliance
        
        Args:
            summary: Raw summary from LLM
            roast_mode: Whether it's roast mode
            
        Returns:
            Processed summary string
        """
        if not summary:
            return summary
        
        # Remove common LLM meta-text patterns
        # 1. Remove quotes if the summary is wrapped in them
        summary = summary.strip()
        if (summary.startswith('"') and summary.endswith('"')) or \
           (summary.startswith("'") and summary.endswith("'")):
            summary = summary[1:-1].strip()
        
        # 2. Remove common prefixes like "摘要：", "吐槽：", "答案是", etc.
        prefixes_to_remove = [
            "摘要：", "摘要:", "吐槽：", "吐槽:", "答案是", "答案:", 
            "输出:", "输出：", "结果:", "结果：", "Summary:", "summary:"
        ]
        for prefix in prefixes_to_remove:
            if summary.startswith(prefix):
                summary = summary[len(prefix):].strip()
                break
        
        # 3. Remove explanations after the summary (common pattern: "摘要: XXXX 这是因为...")
        # Split on common explanation markers and take the first part
        for marker in ["这是因为", "原因是", "这是由于", "这表明", "这说明"]:
            if marker in summary:
                summary = summary.split(marker)[0].strip()
        
        # 4. Clean up prompt leak patterns (for roast mode)
        if roast_mode:
            # Remove markdown headings and bold markers
            summary = re.sub(r'^#{1,6}\s*', '', summary, flags=re.MULTILINE)  # Remove # headings
            summary = re.sub(r'\*\*([^*]+)\*\*', r'\1', summary)  # Remove **bold**
            summary = re.sub(r'\*([^*]+)\*', r'\1', summary)  # Remove *italic*
            
            # Remove numbered list markers at line start
            summary = re.sub(r'^\s*\d+\.\s*', '', summary, flags=re.MULTILINE)
            
            # Remove common prompt leak keywords and patterns
            prompt_leak_patterns = [
                r'分析请求[:：]?\s*',
                r'角色[:：]?\s*',
                r'任务[:：]?\s*',
                r'要求[:：]?\s*',
                r'\*\*分析请求\*\*[:：]?\s*',
                r'\*\*角色\*\*[:：]?\s*',
                r'\*\*任务\*\*[:：]?\s*',
                r'\*\*要求\*\*[:：]?\s*',
                r'你是一个[^，。！？]*[，。！？]\s*',
                r'新闻标题[:：]?[^\n]*\n',
                r'新闻内容[:：]?[^\n]*\n',
                r'只输出吐槽内容[^\n]*\n',
                r'不要任何解释[^\n]*\n',
            ]
            
            for pattern in prompt_leak_patterns:
                summary = re.sub(pattern, '', summary, flags=re.IGNORECASE)
            
            # Remove any remaining markdown code blocks
            summary = re.sub(r'```[^\n]*\n?', '', summary)
            summary = re.sub(r'```$', '', summary)
            
            # Remove extra whitespace and newlines
            summary = re.sub(r'\n{3,}', '\n\n', summary)
        
        # 5. Apply length limits
        max_length = 30 if roast_mode else 25
        if len(summary) > max_length:
            # Try to find a good truncation point (period, comma, or ellipsis)
            truncated = summary[:max_length]
            
            # Look for natural break points
            for break_point in ["。", "，", ",", "。", "！", "?", "？", ";", "；"]:
                pos = truncated.rfind(break_point)
                if pos > max_length * 0.7:  # Only break if it's at least 70% of max length
                    summary = truncated[:pos + 1]
                    break
            else:
                # No good break point found, just truncate and add ellipsis
                summary = truncated[:-1] + "…"
        
        # Final strip
        summary = summary.strip()
        
        logger.debug(f"Post-processed summary ({len(summary)} chars): {summary[:50]}...")
        return summary
    
    def batch_summarize(self, articles: list, roast_mode: bool = False) -> list:
        """
        Batch process multiple articles
        
        Args:
            articles: List of dicts with 'title', 'content', and optional 'topic' keys
            roast_mode: Whether to use roast mode
        
        Returns:
            List of articles with added 'summary' field
        """
        results = []
        
        for article in articles:
            try:
                summary = self.generate_summary(
                    article.get("title", ""),
                    article.get("content", ""),
                    roast_mode,
                    article.get("topic")  # Optional topic for RAG enhancement
                )
                article["summary"] = summary
                results.append(article)
            except Exception as e:
                logger.error(f"Batch summarize error: {str(e)}")
                article["summary"] = self._fallback_summary(
                    article.get("title", ""),
                    article.get("content", ""),
                    roast_mode
                )
                results.append(article)
        
        return results


# Singleton instance
_summarizer_instance = None

def get_summarizer() -> NewsSummarizer:
    """Get singleton summarizer instance"""
    global _summarizer_instance
    if _summarizer_instance is None:
        _summarizer_instance = NewsSummarizer()
    return _summarizer_instance
