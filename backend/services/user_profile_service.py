"""
User Profile Service Module

Manages user interest profiles based on reading history and provides
personalized recommendations using vector-based similarity.
"""

import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta

from rag.embedding_service import EmbeddingService, get_embedding_service
from rag.retrieval_service import RetrievalService, get_retrieval_service

try:
    from sqlalchemy.orm import Session
    from models import UserNewsInteraction, NewsCache, UserPreference
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    logging.warning("SQLAlchemy models not available")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UserProfileService:
    """Service for managing user interest profiles and personalized recommendations"""
    
    def __init__(
        self,
        embedding_service: Optional[EmbeddingService] = None,
        retrieval_service: Optional[RetrievalService] = None
    ):
        """
        Initialize user profile service
        
        Args:
            embedding_service: Embedding service instance
            retrieval_service: Retrieval service instance
        """
        self.embedding_service = embedding_service or get_embedding_service()
        self.retrieval_service = retrieval_service or get_retrieval_service()
        self.is_available = (
            self.embedding_service.is_available and 
            self.retrieval_service.is_available and
            SQLALCHEMY_AVAILABLE
        )
        
        if not self.is_available:
            logger.warning("User profile service not available. Missing dependencies.")
    
    def build_user_interest_profile(
        self,
        db: Session,
        user_id: int,
        lookback_days: int = 30
    ) -> Optional[List[float]]:
        """
        Build user interest profile vector based on reading history
        
        Args:
            db: Database session
            user_id: User ID
            lookback_days: Number of days to look back in reading history
        
        Returns:
            User interest profile vector or None if failed
        """
        if not self.is_available:
            logger.warning("User profile service not available")
            return None
        
        try:
            # Calculate cutoff date
            cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
            
            # Get user's reading history
            interactions = db.query(UserNewsInteraction).filter(
                UserNewsInteraction.user_id == user_id,
                UserNewsInteraction.is_read == True,
                UserNewsInteraction.read_at >= cutoff_date
            ).order_by(UserNewsInteraction.read_at.desc()).all()
            
            if not interactions:
                logger.debug(f"No reading history found for user {user_id}")
                return None
            
            # Get news content for read articles
            news_ids = [interaction.news_id for interaction in interactions]
            read_news = db.query(NewsCache).filter(
                NewsCache.id.in_(news_ids)
            ).all()
            
            if not read_news:
                return None
            
            # Create news ID to article mapping
            news_map = {news.id: news for news in read_news}
            
            # Build interest texts with recency weighting
            interest_texts = []
            weights = []
            
            for interaction in interactions:
                news = news_map.get(interaction.news_id)
                if not news:
                    continue
                
                # Combine title and summary
                combined_text = f"{news.title} {news.summary}"[:500]
                interest_texts.append(combined_text)
                
                # Calculate weight based on recency (more recent = higher weight)
                days_ago = (datetime.utcnow() - interaction.read_at).days
                weight = max(0.5, 1.0 - (days_ago / lookback_days) * 0.5)
                weights.append(weight)
            
            if not interest_texts:
                return None
            
            # Generate embeddings
            embeddings = self.embedding_service.generate_embeddings_batch(interest_texts)
            
            # Filter valid embeddings and apply weights
            valid_embeddings = []
            valid_weights = []
            
            for i, emb in enumerate(embeddings):
                if emb is not None:
                    valid_embeddings.append(emb)
                    valid_weights.append(weights[i])
            
            if not valid_embeddings:
                logger.warning("No valid embeddings generated for user profile")
                return None
            
            # Weighted average of embeddings
            user_profile = self._weighted_average_embeddings(
                valid_embeddings,
                valid_weights
            )
            
            logger.debug(f"Built user profile for user {user_id} from {len(valid_embeddings)} articles")
            return user_profile
            
        except Exception as e:
            logger.error(f"Failed to build user interest profile: {str(e)}")
            return None
    
    def get_topic_preferences(
        self,
        db: Session,
        user_id: int,
        lookback_days: int = 30
    ) -> Dict[str, float]:
        """
        Analyze user's topic preferences based on reading history
        
        Args:
            db: Database session
            user_id: User ID
            lookback_days: Number of days to look back
        
        Returns:
            Dictionary mapping topics to preference scores
        """
        if not SQLALCHEMY_AVAILABLE:
            return {}
        
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
            
            # Get topic reading counts
            topic_counts = db.query(
                NewsCache.topic,
                func.count(UserNewsInteraction.id).label('read_count')
            ).join(
                UserNewsInteraction,
                NewsCache.id == UserNewsInteraction.news_id
            ).filter(
                UserNewsInteraction.user_id == user_id,
                UserNewsInteraction.is_read == True,
                UserNewsInteraction.read_at >= cutoff_date
            ).group_by(
                NewsCache.topic
            ).all()
            
            if not topic_counts:
                return {}
            
            # Calculate total reads
            total_reads = sum(count for _, count in topic_counts)
            
            if total_reads == 0:
                return {}
            
            # Calculate preference scores (normalized to 0-1)
            topic_preferences = {}
            for topic, count in topic_counts:
                topic_preferences[topic] = count / total_reads
            
            logger.debug(f"Topic preferences for user {user_id}: {topic_preferences}")
            return topic_preferences
            
        except Exception as e:
            logger.error(f"Failed to analyze topic preferences: {str(e)}")
            return {}
    
    def get_source_preferences(
        self,
        db: Session,
        user_id: int,
        lookback_days: int = 30
    ) -> Dict[str, float]:
        """
        Analyze user's source preferences based on reading history
        
        Args:
            db: Database session
            user_id: User ID
            lookback_days: Number of days to look back
        
        Returns:
            Dictionary mapping sources to preference scores
        """
        if not SQLALCHEMY_AVAILABLE:
            return {}
        
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
            
            # Get source reading counts
            source_counts = db.query(
                NewsCache.source,
                func.count(UserNewsInteraction.id).label('read_count')
            ).join(
                UserNewsInteraction,
                NewsCache.id == UserNewsInteraction.news_id
            ).filter(
                UserNewsInteraction.user_id == user_id,
                UserNewsInteraction.is_read == True,
                UserNewsInteraction.read_at >= cutoff_date,
                NewsCache.source.isnot(None)
            ).group_by(
                NewsCache.source
            ).all()
            
            if not source_counts:
                return {}
            
            # Calculate total reads
            total_reads = sum(count for _, count in source_counts)
            
            if total_reads == 0:
                return {}
            
            # Calculate preference scores
            source_preferences = {}
            for source, count in source_counts:
                if source:  # Skip None sources
                    source_preferences[source] = count / total_reads
            
            return source_preferences
            
        except Exception as e:
            logger.error(f"Failed to analyze source preferences: {str(e)}")
            return {}
    
    def get_reading_patterns(
        self,
        db: Session,
        user_id: int,
        lookback_days: int = 30
    ) -> Dict[str, Any]:
        """
        Analyze user's reading patterns and behavior
        
        Args:
            db: Database session
            user_id: User ID
            lookback_days: Number of days to look back
        
        Returns:
            Dictionary containing reading pattern analysis
        """
        if not SQLALCHEMY_AVAILABLE:
            return {}
        
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
            
            # Get all interactions in the period
            interactions = db.query(UserNewsInteraction).filter(
                UserNewsInteraction.user_id == user_id,
                UserNewsInteraction.is_read == True,
                UserNewsInteraction.read_at >= cutoff_date
            ).all()
            
            if not interactions:
                return {}
            
            # Calculate reading frequency
            days_with_reads = set()
            hourly_distribution = [0] * 24
            
            for interaction in interactions:
                read_time = interaction.read_at
                days_with_reads.add(read_time.date())
                hourly_distribution[read_time.hour] += 1
            
            # Find peak reading hour
            peak_hour = hourly_distribution.index(max(hourly_distribution))
            
            # Calculate average reads per day
            total_days = max(1, len(days_with_reads))
            avg_reads_per_day = len(interactions) / total_days
            
            patterns = {
                "total_reads": len(interactions),
                "days_active": len(days_with_reads),
                "average_reads_per_day": round(avg_reads_per_day, 2),
                "peak_reading_hour": peak_hour,
                "hourly_distribution": hourly_distribution,
                "activity_period_days": min(lookback_days, (datetime.utcnow() - min(i.read_at for i in interactions).replace(tzinfo=None)).days)
            }
            
            return patterns
            
        except Exception as e:
            logger.error(f"Failed to analyze reading patterns: {str(e)}")
            return {}
    
    def generate_comprehensive_profile(
        self,
        db: Session,
        user_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Generate comprehensive user profile including interests, preferences, and patterns
        
        Args:
            db: Database session
            user_id: User ID
        
        Returns:
            Comprehensive user profile or None if failed
        """
        if not self.is_available:
            return None
        
        try:
            # Build interest vector
            interest_vector = self.build_user_interest_profile(db, user_id)
            
            # Analyze preferences
            topic_preferences = self.get_topic_preferences(db, user_id)
            source_preferences = self.get_source_preferences(db, user_id)
            reading_patterns = self.get_reading_patterns(db, user_id)
            
            # Combine into comprehensive profile
            profile = {
                "user_id": user_id,
                "generated_at": datetime.utcnow().isoformat(),
                "interest_vector_available": interest_vector is not None,
                "vector_dimension": len(interest_vector) if interest_vector else 0,
                "topic_preferences": topic_preferences,
                "source_preferences": source_preferences,
                "reading_patterns": reading_patterns
            }
            
            return profile
            
        except Exception as e:
            logger.error(f"Failed to generate comprehensive profile: {str(e)}")
            return None
    
    def _weighted_average_embeddings(
        self,
        embeddings: List[List[float]],
        weights: List[float]
    ) -> List[float]:
        """
        Calculate weighted average of embeddings
        
        Args:
            embeddings: List of embedding vectors
            weights: Weights for each embedding
        
        Returns:
            Weighted average embedding vector
        """
        try:
            import numpy as np
            
            # Convert to numpy arrays
            emb_array = np.array(embeddings)
            weight_array = np.array(weights)
            
            # Normalize weights
            weight_array = weight_array / np.sum(weight_array)
            
            # Calculate weighted average
            weighted_avg = np.average(emb_array, axis=0, weights=weight_array)
            
            # Normalize the result
            norm = np.linalg.norm(weighted_avg)
            if norm > 0:
                weighted_avg = weighted_avg / norm
            
            return weighted_avg.tolist()
            
        except Exception as e:
            logger.error(f"Failed to calculate weighted average embeddings: {str(e)}")
            # Fallback to simple average
            if embeddings:
                import numpy as np
                avg = np.mean(np.array(embeddings), axis=0)
                return avg.tolist()
            return []


# Singleton instance
_user_profile_service_instance = None


def get_user_profile_service() -> UserProfileService:
    """Get singleton user profile service instance"""
    global _user_profile_service_instance
    if _user_profile_service_instance is None:
        _user_profile_service_instance = UserProfileService()
    return _user_profile_service_instance
