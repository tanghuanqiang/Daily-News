"""
Vector Store Module using ChromaDB

Provides persistent storage and retrieval of news embeddings for RAG functionality.
"""

import os
import logging
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
import uuid

try:
    import chromadb
    from chromadb.config import Settings
    from chromadb.api.models.Collection import Collection
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False
    logging.warning("ChromaDB not available. RAG features will be disabled.")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VectorStore:
    """Vector database wrapper for storing and retrieving news embeddings"""
    
    def __init__(self, persist_directory: str = "./chroma_db"):
        """
        Initialize ChromaDB client and collection
        
        Args:
            persist_directory: Directory to persist vector database
        """
        self.persist_directory = persist_directory
        self.client = None
        self.collection = None
        self.is_available = CHROMA_AVAILABLE
        
        if not CHROMA_AVAILABLE:
            logger.warning("ChromaDB not installed. Vector store will be disabled.")
            return
        
        try:
            # Create persist directory if it doesn't exist
            os.makedirs(persist_directory, exist_ok=True)
            
            # Initialize ChromaDB client with persistence
            self.client = chromadb.PersistentClient(
                path=persist_directory,
                settings=Settings(
                    anonymized_telemetry=False
                )
            )
            
            # Get or create collection for news embeddings
            self.collection = self.client.get_or_create_collection(
                name="news_embeddings",
                metadata={"description": "News article embeddings for RAG"}
            )
            
            logger.info(f"Vector store initialized at {persist_directory}")
            
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {str(e)}")
            self.is_available = False
    
    def add_news(
        self,
        news_id: str,
        title: str,
        content: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Add a news article to the vector store
        
        Args:
            news_id: Unique identifier for the news article
            title: News title
            content: News content/summary
            embedding: Vector embedding of the news content
            metadata: Additional metadata (source, published_at, topic, etc.)
        
        Returns:
            bool: Success status
        """
        if not self.is_available or not self.collection:
            logger.warning("Vector store not available")
            return False
        
        try:
            # Prepare metadata
            doc_metadata = metadata or {}
            doc_metadata.update({
                "title": title,
                "content": content[:500],  # Store truncated content
                "indexed_at": datetime.utcnow().isoformat()
            })
            
            # Generate unique ID
            doc_id = f"news_{news_id}_{uuid.uuid4().hex[:8]}"
            
            # Add to collection
            self.collection.add(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[content],
                metadatas=[doc_metadata]
            )
            
            logger.debug(f"Added news to vector store: {title[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add news to vector store: {str(e)}")
            return False
    
    def search_similar(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar news articles
        
        Args:
            query_embedding: Query vector embedding
            top_k: Number of results to return
            filter_metadata: Optional metadata filters
        
        Returns:
            List of similar news articles with scores
        """
        if not self.is_available or not self.collection:
            logger.warning("Vector store not available")
            return []
        
        try:
            # Perform similarity search
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=filter_metadata,
                include=["documents", "metadatas", "distances"]
            )
            
            # Format results
            formatted_results = []
            if results and results["ids"]:
                for i, doc_id in enumerate(results["ids"][0]):
                    formatted_results.append({
                        "id": doc_id,
                        "content": results["documents"][0][i] if results["documents"] else "",
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "score": 1.0 - results["distances"][0][i] if results["distances"] else 0.0
                    })
            
            logger.debug(f"Found {len(formatted_results)} similar news articles")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Failed to search vector store: {str(e)}")
            return []
    
    def delete_old_news(self, days_to_keep: int = 30) -> int:
        """
        Delete news older than specified days
        
        Args:
            days_to_keep: Keep news from last N days
        
        Returns:
            Number of deleted documents
        """
        if not self.is_available or not self.collection:
            logger.warning("Vector store not available")
            return 0
        
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            
            # Get all documents
            all_docs = self.collection.get(
                include=["metadatas"]
            )
            
            if not all_docs or not all_docs["ids"]:
                return 0
            
            # Find old documents
            old_doc_ids = []
            for i, doc_id in enumerate(all_docs["ids"]):
                metadata = all_docs["metadatas"][i] if all_docs["metadatas"] else {}
                indexed_at_str = metadata.get("indexed_at")
                
                if indexed_at_str:
                    try:
                        indexed_at = datetime.fromisoformat(indexed_at_str)
                        if indexed_at < cutoff_date:
                            old_doc_ids.append(doc_id)
                    except:
                        continue
            
            # Delete old documents
            if old_doc_ids:
                self.collection.delete(ids=old_doc_ids)
                logger.info(f"Deleted {len(old_doc_ids)} old news from vector store")
                return len(old_doc_ids)
            
            return 0
            
        except Exception as e:
            logger.error(f"Failed to delete old news: {str(e)}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics"""
        if not self.is_available or not self.collection:
            return {
                "is_available": False,
                "document_count": 0,
                "storage_size": 0
            }
        
        try:
            # Get collection stats
            collection_info = self.collection
            
            return {
                "is_available": True,
                "document_count": collection_info.count(),
                "persist_directory": self.persist_directory,
                "storage_size": self._get_directory_size(self.persist_directory)
            }
            
        except Exception as e:
            logger.error(f"Failed to get vector store stats: {str(e)}")
            return {"is_available": False, "error": str(e)}
    
    def health_check(self) -> bool:
        """Check if vector store is healthy"""
        if not self.is_available or not self.client:
            return False
        
        try:
            # Try to list collections
            collections = self.client.list_collections()
            return len(collections) > 0
        except:
            return False
    
    def _get_directory_size(self, directory: str) -> int:
        """Calculate directory size in bytes"""
        try:
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(directory):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    if os.path.exists(fp):
                        total_size += os.path.getsize(fp)
            return total_size
        except:
            return 0


# Singleton instance
_vector_store_instance = None


def get_vector_store() -> VectorStore:
    """Get singleton vector store instance"""
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = VectorStore()
    return _vector_store_instance
