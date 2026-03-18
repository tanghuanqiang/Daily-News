"""
Retrieval Service Module

Provides intelligent retrieval of similar news articles using vector similarity
and hybrid search strategies for RAG enhancement.
"""

import logging
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
import re

from .vector_store import VectorStore, get_vector_store
from .embedding_service import EmbeddingService, get_embedding_service

try:
    from sqlalchemy.orm import Session
    from models import NewsCache, UserNewsInteraction, UserPreference
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    logging.warning("SQLAlchemy models not available")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RetrievalService:
    """Intelligent retrieval service for finding similar news articles"""
    
    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        embedding_service: Optional[EmbeddingService] = None
    ):
        """
        Initialize retrieval service
        
        Args:
            vector_store: Vector store instance
            embedding_service: Embedding service instance
        """
        self.vector_store = vector_store or get_vector_store()
        self.embedding_service = embedding_service or get_embedding_service()
        self.is_available = self.vector_store.is_available and self.embedding_service.is_available
        
        if not self.is_available:
            logger.warning("Retrieval service not available. Missing vector store or embedding service.")
    
    def find_similar_news(
        self,
        query_text: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
        min_similarity: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Find similar news articles based on text similarity
        
        Args:
            query_text: Query text to find similar news
            top_k: Number of similar articles to return
            filter_metadata: Optional metadata filters
            min_similarity: Minimum similarity score (0-1)
        
        Returns:
            List of similar news articles with similarity scores
        """
        if not self.is_available:
            logger.warning("Retrieval service not available")
            return []
        
        if not query_text or not query_text.strip():
            logger.warning("Empty query text provided")
            return []
        
        try:
            # Generate embedding for query text
            query_embedding = self.embedding_service.generate_embedding(query_text)
            if not query_embedding:
                logger.error("Failed to generate embedding for query text")
                return []
            
            # Search for similar news
            similar_news = self.vector_store.search_similar(
                query_embedding=query_embedding,
                top_k=top_k * 2,  # Get more results to filter
                filter_metadata=filter_metadata
            )
            
            # Filter by minimum similarity and limit results
            filtered_results = []
            for news in similar_news:
                if news["score"] >= min_similarity:
                    filtered_results.append(news)
                if len(filtered_results) >= top_k:
                    break
            
            logger.debug(f"Found {len(filtered_results)} similar news for query: {query_text[:50]}...")
            return filtered_results
            
        except Exception as e:
            logger.error(f"Failed to find similar news: {str(e)}")
            return []
    
    def find_similar_to_news(
        self,
        news_id: str,
        title: str,
        content: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
        min_similarity: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Find news articles similar to a specific news article
        
        Args:
            news_id: ID of the news article (to exclude from results)
            title: News title
            content: News content
            top_k: Number of similar articles to return
            filter_metadata: Optional metadata filters
            min_similarity: Minimum similarity score (0-1)
        
        Returns:
            List of similar news articles
        """
        if not self.is_available:
            logger.warning("Retrieval service not available")
            return []
        
        try:
            # Combine title and content for better similarity
            combined_text = f"{title} {content}"[:1000]  # Limit length
            
            # Generate embedding
            embedding = self.embedding_service.generate_embedding(combined_text)
            if not embedding:
                logger.error("Failed to generate embedding for news article")
                return []
            
            # Search for similar news
            similar_news = self.vector_store.search_similar(
                query_embedding=embedding,
                top_k=top_k + 1,  # +1 to exclude self
                filter_metadata=filter_metadata
            )
            
            # Filter out the same news and low similarity
            filtered_results = []
            for news in similar_news:
                # Skip if it's the same news
                if news.get("metadata", {}).get("news_id") == news_id:
                    continue
                
                if news["score"] >= min_similarity:
                    filtered_results.append(news)
                
                if len(filtered_results) >= top_k:
                    break
            
            logger.debug(f"Found {len(filtered_results)} news similar to: {title[:50]}...")
            return filtered_results
            
        except Exception as e:
            logger.error(f"Failed to find similar news: {str(e)}")
            return []
    
    def get_personalized_recommendations(
        self,
        db: Session,
        user_id: int,
        topic: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get personalized news recommendations based on user's reading history
        
        Args:
            db: Database session
            user_id: User ID
            topic: Optional topic filter
            limit: Number of recommendations
        
        Returns:
            List of recommended news articles
        """
        if not SQLALCHEMY_AVAILABLE:
            logger.warning("SQLAlchemy not available")
            return []
        
        if not self.is_available:
            logger.warning("Retrieval service not available")
            return []
        
        try:
            # Get user's recent read news
            recent_reads = db.query(UserNewsInteraction).filter(
                UserNewsInteraction.user_id == user_id,
                UserNewsInteraction.is_read == True
            ).order_by(UserNewsInteraction.read_at.desc()).limit(20).all()
            
            if not recent_reads:
                logger.debug(f"No reading history found for user {user_id}")
                return []
            
            # Get news content for recent reads
            news_ids = [interaction.news_id for interaction in recent_reads]
            recent_news = db.query(NewsCache).filter(
                NewsCache.id.in_(news_ids)
            ).all()
            
            if not recent_news:
                return []
            
            # Build user interest profile from recent reads
            interest_texts = []
            for news in recent_news:
                # Combine title and summary, weighted by recency
                interest_texts.append(f"{news.title} {news.summary}")
            
            if not interest_texts:
                return []
            
            # Generate embeddings for user's interest profile
            interest_embeddings = self.embedding_service.generate_embeddings_batch(
                interest_texts[:10]  # Limit to recent 10 for performance
            )
            
            # Filter valid embeddings
            valid_embeddings = [emb for emb in interest_embeddings if emb is not None]
            
            if not valid_embeddings:
                logger.warning("No valid embeddings generated for user interest profile")
                return []
            
            # Average embeddings to create user profile vector
            user_profile_vector = self._average_embeddings(valid_embeddings)
            
            # Build filter for unread news
            filter_metadata = {}
            if topic:
                filter_metadata["topic"] = topic
            
            # Search for news similar to user profile
            similar_news = self.vector_store.search_similar(
                query_embedding=user_profile_vector,
                top_k=limit * 2,  # Get more to filter out already read
                filter_metadata=filter_metadata
            )
            
            # Filter out already read news
            recommendations = []
            for news in similar_news:
                news_id = self._extract_news_id(news.get("id", ""))
                if news_id and int(news_id) in news_ids:
                    continue  # Skip already read
                
                if len(recommendations) >= limit:
                    break
                
                recommendations.append(news)
            
            logger.debug(f"Generated {len(recommendations)} personalized recommendations for user {user_id}")
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to generate personalized recommendations: {str(e)}")
            return []
    
    def hybrid_search(
        self,
        query_text: str,
        db: Session,
        topic: Optional[str] = None,
        limit: int = 10,
        time_weight: float = 0.3,
        similarity_weight: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search combining vector similarity and time-based scoring
        
        Args:
            query_text: Search query
            db: Database session
            topic: Optional topic filter
            limit: Number of results
            time_weight: Weight for time recency (0-1)
            similarity_weight: Weight for vector similarity (0-1)
        
        Returns:
            Ranked list of news articles
        """
        if not self.is_available:
            logger.warning("Retrieval service not available")
            return []
        
        try:
            # Get vector similarity results
            vector_results = self.find_similar_news(
                query_text=query_text,
                top_k=limit * 2,
                filter_metadata={"topic": topic} if topic else None
            )
            
            if not vector_results:
                return []
            
            # Build hybrid scores
            hybrid_results = []
            for result in vector_results:
                # Vector similarity score (0-1)
                similarity_score = result.get("score", 0.0)
                
                # Time recency score (0-1, more recent = higher)
                time_score = self._calculate_time_score(
                    result.get("metadata", {}).get("indexed_at")
                )
                
                # Combine scores
                hybrid_score = (
                    similarity_score * similarity_weight +
                    time_score * time_weight
                )
                
                hybrid_results.append({
                    **result,
                    "hybrid_score": hybrid_score,
                    "similarity_score": similarity_score,
                    "time_score": time_score
                })
            
            # Sort by hybrid score
            hybrid_results.sort(key=lambda x: x["hybrid_score"], reverse=True)
            
            # Return top results
            return hybrid_results[:limit]
            
        except Exception as e:
            logger.error(f"Hybrid search failed: {str(e)}")
            return []
    
    def extract_keywords_from_news(
        self,
        title: str,
        content: str,
        top_k: int = 5
    ) -> List[str]:
        """
        Extract keywords from news title and content
        
        Args:
            title: News title
            content: News content
            top_k: Number of keywords to extract
        
        Returns:
            List of extracted keywords
        """
        try:
            # Combine title and content
            full_text = f"{title} {content}"
            
            # Simple keyword extraction (in production, use libraries like jieba or LLM)
            # For now, extract nouns and important terms
            words = re.findall(r'\b[A-Za-z]{3,}\b|[\u4e00-\u9fff]{2,}', full_text)
            
            # Count word frequency
            word_freq = {}
            for word in words:
                if len(word) > 2:  # Filter short words
                    word_freq[word] = word_freq.get(word, 0) + 1
            
            # Sort by frequency and return top k
            sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
            keywords = [word for word, freq in sorted_words[:top_k]]
            
            return keywords
            
        except Exception as e:
            logger.error(f"Keyword extraction failed: {str(e)}")
            return []
    
    def _average_embeddings(self, embeddings: List[List[float]]) -> List[float]:
        """Average multiple embeddings to create a centroid"""
        if not embeddings:
            return []
        
        try:
            import numpy as np
            
            # Convert to numpy array
            emb_array = np.array(embeddings)
            
            # Calculate mean
            centroid = np.mean(emb_array, axis=0)
            
            # Convert back to list and normalize
            centroid_list = centroid.tolist()
            norm = np.linalg.norm(centroid_list)
            if norm > 0:
                centroid_list = (centroid / norm).tolist()
            
            return centroid_list
            
        except Exception as e:
            logger.error(f"Failed to average embeddings: {str(e)}")
            # Fallback: return first embedding
            return embeddings[0] if embeddings else []
    
    def _calculate_time_score(self, indexed_at_str: Optional[str]) -> float:
        """Calculate time-based recency score (0-1)"""
        if not indexed_at_str:
            return 0.0
        
        try:
            indexed_at = datetime.fromisoformat(indexed_at_str)
            now = datetime.utcnow()
            
            # Calculate days since indexed
            days_diff = (now - indexed_at).days
            
            # Exponential decay: recent news get higher scores
            # Half-life of 7 days (score = 0.5 after 7 days)
            half_life = 7.0
            time_score = max(0.1, min(1.0, 2 ** (-days_diff / half_life)))
            
            return time_score
            
        except:
            return 0.0
    
    def _extract_news_id(self, doc_id: str) -> Optional[str]:
        """Extract news ID from document ID"""
        try:
            # Document ID format: news_{news_id}_{uuid}
            if doc_id.startswith("news_"):
                parts = doc_id.split("_")
                if len(parts) >= 2:
                    return parts[1]
            return None
        except:
            return None


# Singleton instance
_retrieval_service_instance = None


def get_retrieval_service() -> RetrievalService:
    """Get singleton retrieval service instance"""
    global _retrieval_service_instance
    if _retrieval_service_instance is None:
        _retrieval_service_instance = RetrievalService()
    return _retrieval_service_instance
