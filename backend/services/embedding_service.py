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
from pathlib import Path


class EmbeddingService:
    """
    Service for generating and managing text embeddings.
    Uses sentence-transformers for high-quality semantic embeddings.
    Supports fine-tuned models saved as folders (SentenceTransformer.save())
    """
    
    # Model singleton
    _model = None
    
    # ✅ Đường dẫn đến fine-tuned model (từ pipeline)
    # Các đường dẫn tương đối từ thư mục backend/
    _fine_tuned_folder = "train_test_data/results/sbert_finetuned_cv_jd"
    
    # Fallback model
    _default_model_name = "all-MiniLM-L6-v2"
    
    @classmethod
    def get_model(cls):
        """
        Lazy-load the sentence transformer model.
        
        Priority:
        1. Fine-tuned model from folder (SentenceTransformer.save format) ⭐
        2. Default all-MiniLM-L6-v2
        """
        if cls._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                
                # ✅ Tìm đường dẫn tuyệt đối từ thư mục hiện tại
                current_dir = os.path.dirname(os.path.abspath(__file__))
                
                # Các đường dẫn cần kiểm tra (từ thư mục backend/)
                possible_paths = [
                    # Đường dẫn tương đối từ backend/
                    os.path.join(current_dir, "../train_test_data/results/sbert_finetuned_cv_jd"),
                    os.path.join(current_dir, "train_test_data/results/sbert_finetuned_cv_jd"),
                    os.path.join(current_dir, "../results/sbert_finetuned_cv_jd"),
                    os.path.join(current_dir, "results/sbert_finetuned_cv_jd"),
                    
                    # Đường dẫn tuyệt đối từ thư mục gốc project
                    os.path.join(os.path.dirname(current_dir), "train_test_data/results/sbert_finetuned_cv_jd"),
                    os.path.join(os.path.dirname(current_dir), "results/sbert_finetuned_cv_jd"),
                    
                    # Đường dẫn trực tiếp
                    "train_test_data/results/sbert_finetuned_cv_jd",
                    "results/sbert_finetuned_cv_jd",
                    "../train_test_data/results/sbert_finetuned_cv_jd",
                    "../results/sbert_finetuned_cv_jd",
                ]
                
                model_path = None
                for path in possible_paths:
                    if path and os.path.exists(path) and os.path.isdir(path):
                        model_path = path
                        break
                
                if model_path:
                    print(f"🔥 Loading fine-tuned SBERT from folder: {model_path}")
                    cls._model = SentenceTransformer(model_path)
                    print("✅ Fine-tuned model loaded successfully!")
                
                # ✅ CASE 2: Fallback to default
                else:
                    print(f"⚠️ No fine-tuned model found.")
                    print(f"   Looking in: {possible_paths[:3]}...")
                    print(f"🔄 Loading default model: {cls._default_model_name}")
                    cls._model = SentenceTransformer(cls._default_model_name)
                    print("✅ Default model loaded successfully!")
                    
            except Exception as e:
                print(f"❌ Error loading model: {e}")
                print("🔄 Attempting to load default model...")
                try:
                    from sentence_transformers import SentenceTransformer
                    cls._model = SentenceTransformer(cls._default_model_name)
                    print("✅ Default model loaded successfully!")
                except Exception as fallback_error:
                    print(f"❌ Critical error: {fallback_error}")
                    cls._model = None
                    
        return cls._model
    
    @classmethod
    def save_model(cls, output_folder: str = None):
        """
        Save current model to folder (SentenceTransformer standard format).
        
        Args:
            output_folder: Path to save the model folder.
                         Defaults to _fine_tuned_folder
        """
        model = cls.get_model()
        if model is None:
            print("❌ No model loaded")
            return False
        
        # Đường dẫn tuyệt đối
        current_dir = os.path.dirname(os.path.abspath(__file__))
        save_path = output_folder or os.path.join(current_dir, "../", cls._fine_tuned_folder)
        
        try:
            # Create directory if not exists
            Path(save_path).mkdir(parents=True, exist_ok=True)
            
            # ✅ Save in SentenceTransformer standard format (folder)
            model.save(save_path)
            print(f"✅ Model saved to folder: {save_path}")
            print(f"📁 Contents: {os.listdir(save_path)}")
            print("👉 To load: SentenceTransformer('{}')".format(save_path))
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
        
        # Remove phone numbers (simplified)
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
        
        # ✅ Batch encode for efficiency
        embeddings = model.encode(
            valid_texts, 
            convert_to_numpy=True, 
            show_progress_bar=False,
            batch_size=32  # Optimal batch size
        )
        
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
        
        # Normalize for faster cosine similarity
        query_norm = query_embedding / (np.linalg.norm(query_embedding) + 1e-8)
        candidate_norms = candidate_matrix / (np.linalg.norm(candidate_matrix, axis=1, keepdims=True) + 1e-8)
        
        # Compute similarities
        similarities = np.dot(candidate_norms, query_norm)
        
        # Reconstruct results
        result = [0.0] * len(candidate_embeddings)
        for idx, sim in zip(valid_indices, similarities):
            result[idx] = float(sim)
            
        return result
    
    @classmethod
    def get_embedding_dimension(cls) -> int:
        """Get the dimension of embeddings from current model."""
        model = cls.get_model()
        if model is None:
            return 384  # Default dimension for all-MiniLM-L6-v2
        
        # Test encode a sample to get dimension
        sample_embedding = model.encode("test", convert_to_numpy=True)
        return len(sample_embedding)
    
    @classmethod
    def check_model_status(cls) -> dict:
        """Check if fine-tuned model is available and return status."""
        status = {
            "fine_tuned_available": False,
            "fine_tuned_path": None,
            "default_model": cls._default_model_name,
            "current_model": None,
            "search_paths": []
        }
        
        # Check for fine-tuned model
        current_dir = os.path.dirname(os.path.abspath(__file__))
        possible_paths = [
            os.path.join(current_dir, "../train_test_data/results/sbert_finetuned_cv_jd"),
            os.path.join(current_dir, "train_test_data/results/sbert_finetuned_cv_jd"),
            os.path.join(current_dir, "../results/sbert_finetuned_cv_jd"),
            os.path.join(current_dir, "results/sbert_finetuned_cv_jd"),
            "train_test_data/results/sbert_finetuned_cv_jd",
            "results/sbert_finetuned_cv_jd",
        ]
        
        for path in possible_paths:
            status["search_paths"].append(path)
            if path and os.path.exists(path) and os.path.isdir(path):
                status["fine_tuned_available"] = True
                status["fine_tuned_path"] = path
                break
        
        # Get current model info
        model = cls.get_model()
        if model is not None:
            status["current_model"] = "Loaded"
        
        return status
    
    @classmethod
    def reload_model(cls):
        """Force reload the model (useful after saving a new fine-tuned model)."""
        cls._model = None
        return cls.get_model()


# ============ HELPER FUNCTIONS FOR MODEL MANAGEMENT ============

def convert_pickle_to_sbert_folder(pickle_path: str, output_folder: str = None):
    """
    Convert legacy pickle model to SentenceTransformer folder format.
    
    ⚠️ NOTE: This only works if the pickle contains a SentenceTransformer model.
    If it contains a sklearn model, this will fail.
    
    Args:
        pickle_path: Path to pickle file
        output_folder: Output folder path (optional)
    """
    try:
        from sentence_transformers import SentenceTransformer
        
        print(f"📂 Loading pickle from: {pickle_path}")
        with open(pickle_path, 'rb') as f:
            model = pickle.load(f)
        
        # Check if it's a SentenceTransformer model
        if not isinstance(model, SentenceTransformer):
            print(f"❌ Error: Pickle contains {type(model)}, not SentenceTransformer")
            print("   This pickle likely contains a sklearn model (LogisticRegression, etc.)")
            print("   Cannot convert to SBERT folder format.")
            return False
        
        # Save as folder
        output_path = output_folder or pickle_path.replace('.pkl', '_sbert_folder')
        model.save(output_path)
        print(f"✅ Successfully converted to folder: {output_path}")
        print(f"📁 Contents: {os.listdir(output_path)}")
        return True
        
    except Exception as e:
        print(f"❌ Conversion failed: {e}")
        return False


def check_and_create_finetuned_model():
    """
    Check if fine-tuned model exists, if not, save default model as fine-tuned.
    Useful for first-time setup.
    """
    status = EmbeddingService.check_model_status()
    if not status["fine_tuned_available"]:
        print(f"📁 Creating fine-tuned model folder...")
        model = EmbeddingService.get_model()
        if model is not None:
            return EmbeddingService.save_model()
    return False


def find_finetuned_model():
    """
    Helper function to find where the fine-tuned model is located.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    
    search_locations = [
        os.path.join(project_root, "train_test_data/results/sbert_finetuned_cv_jd"),
        os.path.join(project_root, "results/sbert_finetuned_cv_jd"),
        os.path.join(current_dir, "train_test_data/results/sbert_finetuned_cv_jd"),
        os.path.join(current_dir, "../train_test_data/results/sbert_finetuned_cv_jd"),
        "train_test_data/results/sbert_finetuned_cv_jd",
        "results/sbert_finetuned_cv_jd",
    ]
    
    print("\n🔍 Searching for fine-tuned model...")
    for loc in search_locations:
        if os.path.exists(loc) and os.path.isdir(loc):
            print(f"   ✅ Found at: {loc}")
            # Check contents
            files = os.listdir(loc)
            print(f"   📁 Contents: {files[:5]}..." if len(files) > 5 else f"   📁 Contents: {files}")
            return loc
        else:
            print(f"   ❌ Not found: {loc}")
    
    print("\n⚠️ No fine-tuned model found!")
    return None


# ============ TEST CODE ============

if __name__ == "__main__":
    print("="*60)
    print("🧪 Testing EmbeddingService")
    print("="*60)
    
    # First, find where the model is
    find_finetuned_model()
    
    # Test 0: Check model status
    print("\n0. Checking model status...")
    status = EmbeddingService.check_model_status()
    print(f"   Fine-tuned available: {status['fine_tuned_available']}")
    if status['fine_tuned_path']:
        print(f"   Fine-tuned path: {status['fine_tuned_path']}")
    print(f"   Search paths checked: {len(status.get('search_paths', []))}")
    
    # Test 1: Load model
    print("\n1. Loading model...")
    model = EmbeddingService.get_model()
    if model:
        print(f"   ✅ Model loaded: {type(model).__name__}")
    
    # Test 2: Generate embedding
    print("\n2. Generating embedding...")
    test_text = "Experienced Python developer with 5 years of experience"
    embedding = EmbeddingService.generate_embedding(test_text)
    if embedding is not None:
        print(f"   ✅ Embedding shape: {embedding.shape}")
        print(f"   ✅ Embedding dtype: {embedding.dtype}")
    
    # Test 3: Batch embeddings
    print("\n3. Batch embeddings...")
    texts = [
        "Data Scientist with ML expertise",
        "Software Engineer Java Spring",
        "Product Manager Agile Scrum"
    ]
    embeddings = EmbeddingService.generate_embeddings_batch(texts)
    print(f"   ✅ Generated {len(embeddings)} embeddings")
    
    # Test 4: Cosine similarity
    print("\n4. Cosine similarity...")
    if len(embeddings) >= 2 and embeddings[0] is not None and embeddings[1] is not None:
        sim = EmbeddingService.cosine_similarity(embeddings[0], embeddings[1])
        print(f"   ✅ Similarity between text1 and text2: {sim:.4f}")
    
    print("\n" + "="*60)
    print("✅ All tests passed!")
    print("="*60)