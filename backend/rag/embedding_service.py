"""
Embedding Service Module

Provides text embedding functionality using sentence-transformers (text2vec-base-chinese).
Generates vector representations of news articles for similarity search.
"""

import os
import logging
from typing import List, Optional, Union
import hashlib
import json
from datetime import datetime, timedelta

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logging.warning("sentence-transformers not available. Text embeddings will be disabled.")

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    logging.warning("numpy not available. Vector operations will be disabled.")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmbeddingService:
    """Text embedding service using sentence-transformers"""
    
    # Default model - text2vec-base-chinese (Chinese optimized)
    DEFAULT_MODEL = "shibing624/text2vec-base-chinese"
    
    # Model cache to avoid reloading
    _model_cache = {}
    
    def __init__(
        self,
        model_name: str = None,
        cache_dir: str = "./models",
        use_cache: bool = True
    ):
        """
        Initialize embedding service
        
        Args:
            model_name: HuggingFace model name or path
            cache_dir: Directory to cache downloaded models
            use_cache: Whether to cache embeddings in memory
        """
        self.model_name = model_name or self.DEFAULT_MODEL
        self.cache_dir = cache_dir
        self.use_cache = use_cache
        self.model = None
        self.is_available = SENTENCE_TRANSFORMERS_AVAILABLE and NUMPY_AVAILABLE
        self._embedding_cache = {}  # In-memory cache
        
        if not self.is_available:
            logger.warning("Embedding service not available. Missing dependencies.")
            return
        
        try:
            # Create cache directory
            os.makedirs(cache_dir, exist_ok=True)
            
            # Load model
            self._load_model()
            
            logger.info(f"Embedding service initialized with model: {self.model_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize embedding service: {str(e)}")
            self.is_available = False
    
    def _load_model(self):
        """Load or retrieve cached model"""
        # Check if model is already in cache
        if self.model_name in self._model_cache:
            self.model = self._model_cache[self.model_name]
            logger.debug(f"Using cached model: {self.model_name}")
            return
        
        try:
            # Load model
            logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(
                self.model_name,
                cache_folder=self.cache_dir
            )
            
            # Cache the model
            self._model_cache[self.model_name] = self.model
            
            logger.info(f"Model loaded successfully. Dimension: {self.model.get_sentence_embedding_dimension()}")
            
        except Exception as e:
            logger.error(f"Failed to load model {self.model_name}: {str(e)}")
            raise
    
    def generate_embedding(
        self,
        text: str,
        use_cache: bool = True
    ) -> Optional[List[float]]:
        """
        Generate embedding for a single text
        
        Args:
            text: Input text to embed
            use_cache: Whether to use caching
        
        Returns:
            List of floats representing the embedding vector, or None if failed
        """
        if not self.is_available or not self.model:
            logger.warning("Embedding service not available")
            return None
        
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            return None
        
        try:
            # Check cache first
            if use_cache and self.use_cache:
                cache_key = self._get_cache_key(text)
                if cache_key in self._embedding_cache:
                    logger.debug(f"Using cached embedding for text: {text[:50]}...")
                    return self._embedding_cache[cache_key]
            
            # Generate embedding
            embedding = self.model.encode(
                text,
                convert_to_numpy=True,
                normalize_embeddings=True
            )
            
            # Convert to list
            embedding_list = embedding.tolist()
            
            # Cache the result
            if use_cache and self.use_cache:
                cache_key = self._get_cache_key(text)
                self._embedding_cache[cache_key] = embedding_list
            
            logger.debug(f"Generated embedding for text: {text[:50]}...")
            return embedding_list
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {str(e)}")
            return None
    
    def generate_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int = 32
    ) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple texts in batch
        
        Args:
            texts: List of input texts
            batch_size: Batch size for processing
        
        Returns:
            List of embedding vectors (or None for failed texts)
        """
        if not self.is_available or not self.model:
            logger.warning("Embedding service not available")
            return [None] * len(texts)
        
        if not texts:
            return []
        
        try:
            # Filter out empty texts
            valid_texts = []
            valid_indices = []
            for i, text in enumerate(texts):
                if text and text.strip():
                    valid_texts.append(text)
                    valid_indices.append(i)
            
            if not valid_texts:
                return [None] * len(texts)
            
            # Generate embeddings in batch
            logger.info(f"Generating embeddings for {len(valid_texts)} texts in batch")
            embeddings = self.model.encode(
                valid_texts,
                batch_size=batch_size,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False
            )
            
            # Convert to list format
            embeddings_list = []
            for emb in embeddings:
                embeddings_list.append(emb.tolist())
            
            # Build result list with None placeholders for empty texts
            results = [None] * len(texts)
            for idx, emb in zip(valid_indices, embeddings_list):
                results[idx] = emb
            
            logger.debug(f"Generated {len([r for r in results if r is not None])} embeddings successfully")
            return results
            
        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {str(e)}")
            return [None] * len(texts)
    
    def calculate_similarity(
        self,
        embedding1: List[float],
        embedding2: List[float]
    ) -> float:
        """
        Calculate cosine similarity between two embeddings
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
        
        Returns:
            Cosine similarity score (0-1)
        """
        if not NUMPY_AVAILABLE:
            logger.warning("numpy not available, cannot calculate similarity")
            return 0.0
        
        try:
            # Convert to numpy arrays
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            # Calculate cosine similarity
            similarity = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
            
            # Ensure it's in range [0, 1]
            similarity = float(max(0.0, min(1.0, similarity)))
            
            return similarity
            
        except Exception as e:
            logger.error(f"Failed to calculate similarity: {str(e)}")
            return 0.0
    
    def get_embedding_dimension(self) -> Optional[int]:
        """Get the dimension of embedding vectors"""
        if not self.is_available or not self.model:
            return None
        
        try:
            return self.model.get_sentence_embedding_dimension()
        except:
            return None
    
    def clear_cache(self):
        """Clear the embedding cache"""
        self._embedding_cache.clear()
        logger.info("Embedding cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "cache_size": len(self._embedding_cache),
            "model_name": self.model_name,
            "is_available": self.is_available,
            "embedding_dimension": self.get_embedding_dimension()
        }
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text"""
        # Use MD5 hash of text as cache key
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def clean_old_cache(self, max_age_hours: int = 24):
        """
        Remove old entries from cache (not implemented for simplicity)
        
        In a production system, you would track cache entry timestamps
        and remove entries older than max_age_hours
        """
        # For now, we just clear the entire cache if it gets too large
        if len(self._embedding_cache) > 10000:
            logger.info(f"Cache too large ({len(self._embedding_cache)} entries), clearing")
            self.clear_cache()


# Alternative: OpenAI Embedding API fallback
class OpenAIEmbeddingService:
    """Fallback embedding service using OpenAI API"""
    
    def __init__(self, api_key: str, model: str = "text-embedding-ada-002"):
        self.api_key = api_key
        self.model = model
        self.is_available = False
        
        try:
            import openai
            self.client = openai.OpenAI(api_key=api_key)
            self.is_available = True
            logger.info("OpenAI embedding service initialized")
        except ImportError:
            logger.warning("OpenAI library not available")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI embedding service: {str(e)}")
    
    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding using OpenAI API"""
        if not self.is_available:
            return None
        
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"OpenAI embedding generation failed: {str(e)}")
            return None


# Singleton instance
_embedding_service_instance = None


def get_embedding_service() -> EmbeddingService:
    """Get singleton embedding service instance"""
    global _embedding_service_instance
    if _embedding_service_instance is None:
        _embedding_service_instance = EmbeddingService()
    return _embedding_service_instance
