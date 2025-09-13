"""
Service for obtaining sentence embeddings
"""

import logging
import numpy as np
from typing import Dict, List, Optional, Union, Any
from datetime import datetime
import time

from ..utils import get_logger


class EmbeddingService:
    """Service for obtaining sentence embeddings"""
    
    def __init__(self, default_model: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """
        Initialize embedding service
        
        Args:
            default_model: Default model
        """
        self.logger = get_logger(__name__)
        self.default_model = default_model
        
        # Popular models for different languages
        self.supported_models = {
            'multilingual': [
                'sentence-transformers/all-MiniLM-L6-v2',
                'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
                'sentence-transformers/LaBSE'
            ],
            'english': [
                'sentence-transformers/all-mpnet-base-v2',
                'sentence-transformers/all-MiniLM-L6-v2'
            ],
            'russian': [
                'DeepPavlov/rubert-base-cased',
                'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
            ],
            'ukrainian': [
                'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
                'DeepPavlov/rubert-base-cased'
            ]
        }
        
        # Model cache
        self.model_cache = {}
        
        self.logger.info(f"EmbeddingService initialized with default model: {default_model}")
    
    def _load_model(self, model_name: str):
        """Load model"""
        try:
            if model_name not in self.model_cache:
                from sentence_transformers import SentenceTransformer
                self.logger.info(f"Loading model: {model_name}")
                model = SentenceTransformer(model_name)
                self.model_cache[model_name] = model
                self.logger.info(f"Model {model_name} loaded successfully")
            
            return self.model_cache[model_name]
        except Exception as e:
            self.logger.error(f"Failed to load model {model_name}: {e}")
            # Fallback to default model
            if model_name != self.default_model:
                return self._load_model(self.default_model)
            raise
    
    def get_embeddings(
        self,
        texts: Union[str, List[str]],
        model_name: Optional[str] = None,
        normalize: bool = True,
        batch_size: int = 32
    ) -> Dict[str, Any]:
        """
        Get embeddings for texts
        
        Args:
            texts: Text or list of texts
            model_name: Model name
            normalize: Normalize embeddings (L2)
            batch_size: Batch size
            
        Returns:
            Dict with embeddings and metadata
        """
        start_time = time.time()
        
        # Normalize input data
        if isinstance(texts, str):
            texts = [texts]
        
        if not texts:
            return self._create_empty_result()
        
        # Use default model if not specified
        if model_name is None:
            model_name = self.default_model
        
        try:
            # Load model
            model = self._load_model(model_name)
            
            # Generate embeddings
            embeddings = model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=False,
                normalize_embeddings=normalize
            )
            
            # Convert to list if needed
            if isinstance(embeddings, np.ndarray):
                # Ensure embeddings is a list
                embeddings = embeddings.tolist()
            
            # Calculate metrics
            processing_time = time.time() - start_time
            
            result = {
                'success': True,
                'embeddings': embeddings,
                'model_name': model_name,
                'text_count': len(texts),
                'embedding_dimension': len(embeddings[0]) if embeddings else 0,
                'processing_time': processing_time,
                'normalized': normalize,
                'batch_size': batch_size,
                'timestamp': datetime.now().isoformat()
            }
            
            self.logger.info(f"Generated embeddings for {len(texts)} texts using model {model_name}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to generate embeddings: {e}")
            return self._create_error_result(str(e))
    
    def calculate_similarity(
        self,
        text1: str,
        text2: str,
        model_name: Optional[str] = None,
        metric: str = 'cosine'
    ) -> Dict[str, Any]:
        """
        Calculate similarity between two texts
        
        Args:
            text1: First text
            text2: Second text
            model_name: Model name
            metric: Similarity metric ('cosine', 'euclidean', 'dot')
            
        Returns:
            Dict with similarity result
        """
        try:
            # Get embeddings
            embeddings_result = self.get_embeddings([text1, text2], model_name)
            
            if not embeddings_result['success']:
                return self._create_error_result("Failed to generate embeddings")
            
            embeddings = embeddings_result['embeddings']
            if len(embeddings) != 2:
                return self._create_error_result("Invalid embeddings result")
            
            # Calculate similarity
            similarity_score = self._calculate_embedding_similarity(
                embeddings[0], embeddings[1], metric
            )
            
            result = {
                'success': True,
                'text1': text1,
                'text2': text2,
                'similarity_score': similarity_score,
                'metric': metric,
                'model_name': embeddings_result['model_name'],
                'processing_time': embeddings_result['processing_time'],
                'timestamp': datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to calculate similarity: {e}")
            return self._create_error_result(str(e))
    
    def find_similar_texts(
        self,
        query: str,
        candidates: List[str],
        model_name: Optional[str] = None,
        threshold: float = 0.7,
        top_k: int = 10,
        metric: str = 'cosine'
    ) -> Dict[str, Any]:
        """
        Search for similar texts among candidates
        
        Args:
            query: Search query
            candidates: List of candidates
            model_name: Model name
            threshold: Similarity threshold
            top_k: Number of best results
            metric: Similarity metric
            
        Returns:
            Dict with search results
        """
        try:
            # Get embeddings for all texts
            all_texts = [query] + candidates
            embeddings_result = self.get_embeddings(all_texts, model_name)
            
            if not embeddings_result['success']:
                return self._create_error_result("Failed to generate embeddings")
            
            embeddings = embeddings_result['embeddings']
            query_embedding = embeddings[0]
            candidate_embeddings = embeddings[1:]
            
            # Calculate similarity with each candidate
            similarities = []
            for i, candidate_embedding in enumerate(candidate_embeddings):
                similarity_score = self._calculate_embedding_similarity(
                    query_embedding, candidate_embedding, metric
                )
                
                similarities.append({
                    'text': candidates[i],
                    'similarity_score': similarity_score,
                    'rank': i + 1
                })
            
            # Filter by threshold and sort
            filtered_similarities = [
                s for s in similarities if s['similarity_score'] >= threshold
            ]
            filtered_similarities.sort(key=lambda x: x['similarity_score'], reverse=True)
            
            # Limit number of results
            top_results = filtered_similarities[:top_k]
            
            result = {
                'success': True,
                'query': query,
                'total_candidates': len(candidates),
                'threshold': threshold,
                'top_k': top_k,
                'metric': metric,
                'results': top_results,
                'model_name': embeddings_result['model_name'],
                'processing_time': embeddings_result['processing_time'],
                'timestamp': datetime.now().isoformat()
            }
            
            self.logger.info(f"Found {len(top_results)} similar texts for query")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to find similar texts: {e}")
            return self._create_error_result(str(e))
    
    def calculate_batch_similarity(
        self,
        text_pairs: List[tuple],
        model_name: Optional[str] = None,
        metric: str = 'cosine'
    ) -> Dict[str, Any]:
        """
        Batch calculation of similarity for text pairs
        
        Args:
            text_pairs: List of text pairs
            model_name: Model name
            metric: Similarity metric
            
        Returns:
            Dict with similarity results
        """
        try:
            # Split pairs into separate texts
            all_texts = []
            pair_indices = []
            
            for i, (text1, text2) in enumerate(text_pairs):
                all_texts.extend([text1, text2])
                pair_indices.append((i * 2, i * 2 + 1))
            
            # Get embeddings
            embeddings_result = self.get_embeddings(all_texts, model_name)
            
            if not embeddings_result['success']:
                return self._create_error_result("Failed to generate embeddings")
            
            embeddings = embeddings_result['embeddings']
            
            # Calculate similarity for each pair
            results = []
            for i, (idx1, idx2) in enumerate(pair_indices):
                text1, text2 = text_pairs[i]
                embedding1 = embeddings[idx1]
                embedding2 = embeddings[idx2]
                
                similarity_score = self._calculate_embedding_similarity(
                    embedding1, embedding2, metric
                )
                
                results.append({
                    'pair_index': i,
                    'text1': text1,
                    'text2': text2,
                    'similarity_score': similarity_score,
                    'metric': metric
                })
            
            result = {
                'success': True,
                'total_pairs': len(text_pairs),
                'metric': metric,
                'results': results,
                'model_name': embeddings_result['model_name'],
                'processing_time': embeddings_result['processing_time'],
                'timestamp': datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to calculate batch similarity: {e}")
            return self._create_error_result(str(e))
    
    def _calculate_embedding_similarity(
        self,
        embedding1: List[float],
        embedding2: List[float],
        metric: str
    ) -> float:
        """Calculate similarity between two embeddings"""
        try:
            # Convert to numpy arrays
            emb1 = np.array(embedding1)
            emb2 = np.array(embedding2)
            
            if metric == 'cosine':
                # Cosine similarity
                dot_product = np.dot(emb1, emb2)
                norm1 = np.linalg.norm(emb1)
                norm2 = np.linalg.norm(emb2)
                
                if norm1 == 0 or norm2 == 0:
                    return 0.0
                
                return dot_product / (norm1 * norm2)
            
            elif metric == 'euclidean':
                # Euclidean distance (convert to similarity)
                distance = np.linalg.norm(emb1 - emb2)
                max_distance = np.linalg.norm(emb1) + np.linalg.norm(emb2)
                
                if max_distance == 0:
                    return 1.0
                
                return 1.0 - (distance / max_distance)
            
            elif metric == 'dot':
                # Dot product
                return np.dot(emb1, emb2)
            
            else:
                raise ValueError(f"Unsupported metric: {metric}")
                
        except Exception as e:
            self.logger.error(f"Failed to calculate similarity: {e}")
            return 0.0
    
    def get_embedding_statistics(self, embeddings: List[List[float]]) -> Dict[str, Any]:
        """Calculate embedding statistics"""
        try:
            # Convert to numpy array
            embeddings_array = np.array(embeddings)
            
            stats = {
                'count': len(embeddings),
                'dimension': embeddings_array.shape[1] if embeddings_array.size > 0 else 0,
                'mean_norm': float(np.mean([np.linalg.norm(emb) for emb in embeddings])),
                'std_norm': float(np.std([np.linalg.norm(emb) for emb in embeddings])),
                'min_norm': float(np.min([np.linalg.norm(emb) for emb in embeddings])),
                'max_norm': float(np.max([np.linalg.norm(emb) for emb in embeddings])),
                'sparsity': float(np.mean([np.count_nonzero(emb) / len(emb) for emb in embeddings]))
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to calculate embedding statistics: {e}")
            return {}
    
    def _create_empty_result(self) -> Dict[str, Any]:
        """Create empty result"""
        return {
            'success': True,
            'embeddings': [],
            'model_name': self.default_model,
            'text_count': 0,
            'embedding_dimension': 0,
            'processing_time': 0.0,
            'normalized': True,
            'batch_size': 32,
            'timestamp': datetime.now().isoformat()
        }
    
    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """Create result with error"""
        return {
            'success': False,
            'error': error_message,
            'embeddings': [],
            'model_name': self.default_model,
            'text_count': 0,
            'embedding_dimension': 0,
            'processing_time': 0.0,
            'normalized': True,
            'batch_size': 32,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_supported_models(self) -> Dict[str, List[str]]:
        """Get list of supported models"""
        return self.supported_models.copy()
    
    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """Get model information"""
        try:
            model = self._load_model(model_name)
            
            info = {
                'name': model_name,
                'max_seq_length': getattr(model, 'max_seq_length', 512),
                'embedding_dimension': model.get_sentence_embedding_dimension(),
                'device': str(model.device),
                'loaded': True
            }
            
            return info
            
        except Exception as e:
            return {
                'name': model_name,
                'error': str(e),
                'loaded': False
            }
    
    def clear_model_cache(self) -> None:
        """Clear model cache"""
        self.model_cache.clear()
        self.logger.info("Model cache cleared")