"""
Embedding Service for the Job Recommendation System.
Handles text embedding generation using sentence-transformers (SBERT).
"""

import numpy as np
from typing import List, Optional, Union
from functools import lru_cache
import re
import os
import pickle


class EmbeddingService:
    """
    Service for generating and managing text embeddings.
    Uses sentence-transformers for high-quality semantic embeddings.
    Supports fine-tuned models saved as pickle files.
    """
    
    # Model singleton
    _model = None
    _model_name = "all-MiniLM-L6-v2"
    
    # Path to fine-tuned model (nếu có)
    _fine_tuned_path = "train_test_data/output/models/Fine-tuned_SBERT.pkl"
    _fine_tuned_folder = "models/fine_tuned_sbert"  # Recommended format
    
    @classmethod
    def get_model(cls):
        """
        Lazy-load the sentence transformer model.
        Priority:
        1. Fine-tuned model from folder (recommended)
        2. Fine-tuned model from pickle file
        3. Default all-MiniLM-L6-v2
        """
        if cls._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                
                # ✅ CASE 1: Load từ folder chuẩn (recommended)
                if os.path.exists(cls._fine_tuned_folder):
                    print(f"🔥 Loading fine-tuned SBERT from folder: {cls._fine_tuned_folder}")
                    cls._model = SentenceTransformer(cls._fine_tuned_folder)
                
                # ✅ CASE 2: Load từ pickle file
                elif os.path.exists(cls._fine_tuned_path):
                    print(f"🔥 Loading fine-tuned SBERT from pickle: {cls._fine_tuned_path}")
                    with open(cls._fine_tuned_path, "rb") as f:
                        cls._model = pickle.load(f)
                    print("✅ Fine-tuned model loaded successfully")
                
                # ✅ CASE 3: Fallback to default
                else:
                    print(f"⚠️ No fine-tuned model found. Loading default: {cls._model_name}")
                    cls._model = SentenceTransformer(cls._model_name)
                    
            except Exception as e:
                print(f"❌ Warning: Could not load fine-tuned model: {e}")
                print("🔄 Falling back to default model...")
                try:
                    from sentence_transformers import SentenceTransformer
                    cls._model = SentenceTransformer(cls._model_name)
                except Exception as fallback_error:
                    print(f"❌ Even default model failed: {fallback_error}")
                    cls._model = None
                    
        return cls._model
    
    @classmethod
    def save_model_as_folder(cls, output_path: str = None):
        """
        Convert pickle model to standard folder format (recommended).
        
        Args:
            output_path: Path to save the model folder. 
                        Defaults to _fine_tuned_folder
        """
        model = cls.get_model()
        if model is None:
            print("❌ No model loaded")
            return False
        
        save_path = output_path or cls._fine_tuned_folder
        try:
            model.save(save_path)
            print(f"✅ Model saved to folder: {save_path}")
            print("👉 Now you can load it with: SentenceTransformer('{}')".format(save_path))
            return True
        except Exception as e:
            print(f"❌ Failed to save model: {e}")
            return False
    
    @classmethod
    def preprocess_text(cls, text: str) -> str:
        """
        Clean and preprocess text for embedding generation.
        
        Args:
            text: Raw text input
            
        Returns:
            Cleaned and normalized text
        """
        if not text:
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove URLs
        text = re.sub(r'http\S+|www\.\S+', '', text)
        
        # Remove email addresses
        text = re.sub(r'\S+@\S+', '', text)
        
        # Remove phone numbers
        text = re.sub(r'[\+]?[(]?[0-9]{1,3}[)]?[-\s\.]?[0-9]{1,4}[-\s\.]?[0-9]{1,4}[-\s\.]?[0-9]{1,9}', '', text)
        
        # Remove special characters but keep important punctuation
        text = re.sub(r'[^\w\s\.\,\-\+\#]', ' ', text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    @classmethod
    def generate_embedding(cls, text: str) -> Optional[np.ndarray]:
        """
        Generate embedding vector for a single text.
        
        Args:
            text: Input text to embed
            
        Returns:
            Numpy array of embedding vector or None if model unavailable
        """
        model = cls.get_model()
        if model is None:
            # Return a mock embedding for development
            print("⚠️ Using mock embedding (model not available)")
            return np.random.rand(384).astype(np.float32)
        
        preprocessed = cls.preprocess_text(text)
        if not preprocessed:
            return None
            
        embedding = model.encode(preprocessed, convert_to_numpy=True)
        return embedding.astype(np.float32)
    
    @classmethod
    def generate_embeddings_batch(cls, texts: List[str]) -> List[Optional[np.ndarray]]:
        """
        Generate embeddings for multiple texts efficiently.
        
        Args:
            texts: List of input texts
            
        Returns:
            List of embedding vectors
        """
        model = cls.get_model()
        if model is None:
            print("⚠️ Using mock embeddings (model not available)")
            return [np.random.rand(384).astype(np.float32) for _ in texts]
        
        preprocessed_texts = [cls.preprocess_text(t) for t in texts]
        
        # Filter out empty texts
        valid_indices = [i for i, t in enumerate(preprocessed_texts) if t]
        valid_texts = [preprocessed_texts[i] for i in valid_indices]
        
        if not valid_texts:
            return [None] * len(texts)
        
        embeddings = model.encode(valid_texts, convert_to_numpy=True, show_progress_bar=False)
        
        # Reconstruct the results with None for empty texts
        result = [None] * len(texts)
        for idx, emb in zip(valid_indices, embeddings):
            result[idx] = emb.astype(np.float32)
            
        return result
    
    @classmethod
    def embedding_to_bytes(cls, embedding: np.ndarray) -> bytes:
        """Convert numpy embedding to bytes for database storage."""
        return embedding.tobytes()
    
    @classmethod
    def bytes_to_embedding(cls, data: bytes) -> np.ndarray:
        """Convert bytes back to numpy embedding."""
        return np.frombuffer(data, dtype=np.float32)
    
    @classmethod
    def cosine_similarity(cls, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """
        Compute cosine similarity between two embeddings.
        
        Args:
            emb1: First embedding vector
            emb2: Second embedding vector
            
        Returns:
            Cosine similarity score between 0 and 1
        """
        if emb1 is None or emb2 is None:
            return 0.0
            
        dot_product = np.dot(emb1, emb2)
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
            
        return float(dot_product / (norm1 * norm2))
    
    @classmethod
    def batch_cosine_similarity(
        cls, 
        query_embedding: np.ndarray, 
        candidate_embeddings: List[np.ndarray]
    ) -> List[float]:
        """
        Compute cosine similarity between a query and multiple candidates.
        
        Args:
            query_embedding: Query embedding vector
            candidate_embeddings: List of candidate embedding vectors
            
        Returns:
            List of similarity scores
        """
        if query_embedding is None:
            return [0.0] * len(candidate_embeddings)
        
        # Stack candidates into a matrix
        valid_candidates = []
        valid_indices = []
        
        for i, emb in enumerate(candidate_embeddings):
            if emb is not None:
                valid_candidates.append(emb)
                valid_indices.append(i)
        
        if not valid_candidates:
            return [0.0] * len(candidate_embeddings)
        
        candidate_matrix = np.vstack(valid_candidates)
        
        # Normalize
        query_norm = query_embedding / np.linalg.norm(query_embedding)
        candidate_norms = candidate_matrix / np.linalg.norm(candidate_matrix, axis=1, keepdims=True)
        
        # Compute similarities
        similarities = np.dot(candidate_norms, query_norm)
        
        # Reconstruct results
        result = [0.0] * len(candidate_embeddings)
        for idx, sim in zip(valid_indices, similarities):
            result[idx] = float(sim)
            
        return result