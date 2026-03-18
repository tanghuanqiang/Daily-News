"""
Knowledge Enhancer Module

Enhances LLM prompts with retrieved context from vector database for better
news summarization and question answering.
"""

import logging
from typing import List, Dict, Optional, Any
from datetime import datetime

from .retrieval_service import RetrievalService, get_retrieval_service
from .embedding_service import EmbeddingService, get_embedding_service

try:
    from sqlalchemy.orm import Session
    from models import NewsCache
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    logging.warning("SQLAlchemy models not available")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KnowledgeEnhancer:
    """Enhances LLM prompts with retrieved knowledge from vector database"""
    
    def __init__(
        self,
        retrieval_service: Optional[RetrievalService] = None,
        embedding_service: Optional[EmbeddingService] = None
    ):
        """
        Initialize knowledge enhancer
        
        Args:
            retrieval_service: Retrieval service instance
            embedding_service: Embedding service instance
        """
        self.retrieval_service = retrieval_service or get_retrieval_service()
        self.embedding_service = embedding_service or get_embedding_service()
        self.is_available = (
            self.retrieval_service.is_available and 
            self.embedding_service.is_available
        )
        
        if not self.is_available:
            logger.warning("Knowledge enhancer not available. Missing dependencies.")
    
    def enhance_summary_prompt(
        self,
        title: str,
        content: str,
        topic: Optional[str] = None,
        top_k: int = 3
    ) -> str:
        """
        Enhance news summary prompt with similar news context
        
        Args:
            title: News title
            content: News content
            topic: News topic/category
            top_k: Number of similar articles to retrieve
        
        Returns:
            Enhanced prompt with retrieved context
        """
        if not self.is_available:
            logger.debug("Knowledge enhancer not available, returning original context")
            return self._build_basic_context(title, content)
        
        try:
            # Retrieve similar news
            similar_news = self.retrieval_service.find_similar_to_news(
                news_id="",
                title=title,
                content=content,
                top_k=top_k,
                filter_metadata={"topic": topic} if topic else None,
                min_similarity=0.4
            )
            
            # Build enhanced context
            if similar_news:
                return self._build_enhanced_context(title, content, similar_news, topic)
            else:
                return self._build_basic_context(title, content)
            
        except Exception as e:
            logger.error(f"Failed to enhance summary prompt: {str(e)}")
            return self._build_basic_context(title, content)
    
    def enhance_roast_prompt(
        self,
        title: str,
        content: str,
        topic: Optional[str] = None,
        top_k: int = 2
    ) -> str:
        """
        Enhance roast/troll summary prompt with similar news context
        
        Args:
            title: News title
            content: News content
            topic: News topic/category
            top_k: Number of similar articles to retrieve
        
        Returns:
            Enhanced roast prompt
        """
        if not self.is_available:
            logger.debug("Knowledge enhancer not available, returning original context")
            return self._build_basic_roast_context(title, content)
        
        try:
            # Retrieve similar news
            similar_news = self.retrieval_service.find_similar_to_news(
                news_id="",
                title=title,
                content=content,
                top_k=top_k,
                filter_metadata={"topic": topic} if topic else None,
                min_similarity=0.4
            )
            
            # Build enhanced roast context
            if similar_news:
                return self._build_enhanced_roast_context(title, content, similar_news, topic)
            else:
                return self._build_basic_roast_context(title, content)
            
        except Exception as e:
            logger.error(f"Failed to enhance roast prompt: {str(e)}")
            return self._build_basic_roast_context(title, content)
    
    def generate_context_for_question(
        self,
        question: str,
        db: Session,
        topic: Optional[str] = None,
        top_k: int = 5
    ) -> str:
        """
        Generate context for answering user questions about news
        
        Args:
            question: User question
            db: Database session
            topic: Optional topic filter
            top_k: Number of relevant articles
        
        Returns:
            Context string for LLM prompt
        """
        if not self.is_available or not SQLALCHEMY_AVAILABLE:
            logger.debug("Knowledge enhancer not available")
            return ""
        
        try:
            # Extract keywords from question
            keywords = self.retrieval_service.extract_keywords_from_news(
                title=question,
                content=question,
                top_k=5
            )
            
            # Search for relevant news
            relevant_news = self.retrieval_service.find_similar_news(
                query_text=question,
                top_k=top_k,
                filter_metadata={"topic": topic} if topic else None
            )
            
            # Build context
            if relevant_news:
                return self._build_question_context(question, relevant_news, keywords)
            else:
                return self._build_basic_question_context(question)
            
        except Exception as e:
            logger.error(f"Failed to generate context for question: {str(e)}")
            return ""
    
    def _build_basic_context(self, title: str, content: str) -> str:
        """Build basic context without enhancements"""
        return f"""新闻标题：{title}

新闻内容：{content}

请总结这条新闻的核心内容。"""
    
    def _build_enhanced_context(
        self,
        title: str,
        content: str,
        similar_news: List[Dict[str, Any]],
        topic: Optional[str] = None
    ) -> str:
        """Build enhanced context with similar news"""
        context_parts = [
            f"新闻标题：{title}",
            f"新闻内容：{content}\n",
            "相关背景信息："
        ]
        
        # Add similar news as context
        for i, news in enumerate(similar_news, 1):
            metadata = news.get("metadata", {})
            news_title = metadata.get("title", f"相关新闻 {i}")
            news_content = news.get("content", "")
            similarity_score = news.get("score", 0)
            
            context_parts.append(
                f"{i}. {news_title} (相关性: {similarity_score:.2f})\n"
                f"   {news_content[:200]}...\n"
            )
        
        context_parts.extend([
            "\n基于以上新闻及其背景信息，",
            "请总结当前新闻的核心内容，",
            "并可以引用相关背景信息提供更全面的解读。"
        ])
        
        return "\n".join(context_parts)
    
    def _build_basic_roast_context(self, title: str, content: str) -> str:
        """Build basic roast context without enhancements"""
        return f"""你是一个幽默风趣的新闻评论员，擅长用俏皮、搞笑、略带吐槽的语气总结新闻。

新闻标题：{title}
新闻内容：{content}

请用1-2句话总结这条新闻，要求：
1. 语气幽默、俏皮，可以适当调侃
2. 抓住新闻核心要点
3. 加入一些网络流行语或段子风格
4. 保持简洁，不超过60字

吐槽式摘要："""
    
    def _build_enhanced_roast_context(
        self,
        title: str,
        content: str,
        similar_news: List[Dict[str, Any]],
        topic: Optional[str] = None
    ) -> str:
        """Build enhanced roast context with similar news"""
        context_parts = [
            "你是一个幽默风趣的新闻评论员，擅长用俏皮、搞笑、略带吐槽的语气总结新闻。",
            "请结合相关新闻背景进行有趣的对比和调侃。\n",
            f"新闻标题：{title}",
            f"新闻内容：{content}\n",
            "相关新闻背景（可用于对比和调侃）："
        ]
        
        # Add similar news for context
        for i, news in enumerate(similar_news[:2], 1):  # Limit to 2 for roast mode
            metadata = news.get("metadata", {})
            news_title = metadata.get("title", f"相关新闻 {i}")
            news_content = news.get("content", "")
            
            context_parts.append(
                f"{i}. {news_title}\n"
                f"   {news_content[:150]}...\n"
            )
        
        context_parts.extend([
            "\n请用1-2句话吐槽这条新闻，可以：",
            "- 和背景新闻进行对比",
            "- 指出其中的矛盾或槽点",
            "- 用幽默的方式总结核心要点",
            "- 适当加入网络流行语",
            "保持简洁，不超过60字。\n",
            "吐槽式摘要："
        ])
        
        return "\n".join(context_parts)
    
    def _build_question_context(
        self,
        question: str,
        relevant_news: List[Dict[str, Any]],
        keywords: List[str]
    ) -> str:
        """Build context for answering questions"""
        context_parts = [
            f"用户问题：{question}\n",
            "关键词：" + ", ".join(keywords[:5]) + "\n",
            "相关新闻信息："
        ]
        
        # Add relevant news
        for i, news in enumerate(relevant_news, 1):
            metadata = news.get("metadata", {})
            news_title = metadata.get("title", f"相关新闻 {i}")
            news_content = news.get("content", "")
            similarity_score = news.get("score", 0)
            
            context_parts.append(
                f"{i}. {news_title}\n"
                f"   内容：{news_content[:300]}...\n"
                f"   相关性：{similarity_score:.2f}\n"
            )
        
        context_parts.extend([
            "\n基于以上新闻信息，请回答用户的问题。",
            "如果信息不足，请明确说明。",
            "请提供准确、简洁的答案，并引用相关新闻来源。"
        ])
        
        return "\n".join(context_parts)
    
    def _build_basic_question_context(self, question: str) -> str:
        """Build basic context for questions"""
        return f"""用户问题：{question}

请基于你的知识回答这个问题。如果无法回答，请明确说明。"""


# Singleton instance
_knowledge_enhancer_instance = None


def get_knowledge_enhancer() -> KnowledgeEnhancer:
    """Get singleton knowledge enhancer instance"""
    global _knowledge_enhancer_instance
    if _knowledge_enhancer_instance is None:
        _knowledge_enhancer_instance = KnowledgeEnhancer()
    return _knowledge_enhancer_instance
