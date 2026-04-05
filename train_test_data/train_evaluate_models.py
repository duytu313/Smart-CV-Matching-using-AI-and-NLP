"""
JOB MATCHING MODEL TRAINING PIPELINE - PRODUCTION READY (FIXED)
Author: Professional ML Engineer
Version: 2.1.1
Description: Production-grade training pipeline for job matching models with ranking metrics
"""

import numpy as np
import pandas as pd
from sklearn.metrics import (accuracy_score, precision_score, recall_score, 
                           f1_score, roc_auc_score, confusion_matrix, 
                           matthews_corrcoef, classification_report)
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
from sklearn.svm import SVC
from sklearn.calibration import CalibratedClassifierCV
import pickle
import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# NLP Libraries
from sentence_transformers import SentenceTransformer, InputExample, losses
from torch.utils.data import DataLoader
import torch
from gensim.models import Word2Vec
from gensim.utils import simple_preprocess
import nltk
from nltk.corpus import stopwords

# Visualization
import matplotlib.pyplot as plt
import seaborn as sns
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('output/training.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Download NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)

# ============ RANKING METRICS ============

def ndcg_at_k(relevance_scores: List[float], k: int = 10) -> float:
    """
    Calculate NDCG@k (Normalized Discounted Cumulative Gain)
    
    Args:
        relevance_scores: List of relevance scores (0 or 1)
        k: Number of top results to consider
    
    Returns:
        NDCG@k score (0-1)
    """
    if len(relevance_scores) == 0:
        return 0.0
    
    # Take top-k
    relevance_scores = relevance_scores[:k]
    
    # Calculate DCG
    dcg = 0.0
    for i, rel in enumerate(relevance_scores):
        dcg += rel / np.log2(i + 2)  # i+2 because log2(1+1)=log2(2)=1
    
    # Calculate IDCG (Ideal DCG)
    ideal_scores = sorted(relevance_scores, reverse=True)
    idcg = 0.0
    for i, rel in enumerate(ideal_scores):
        idcg += rel / np.log2(i + 2)
    
    # Return NDCG
    if idcg == 0:
        return 0.0
    return dcg / idcg

def mrr_at_k(relevance_scores: List[float], k: int = 10) -> float:
    """
    Calculate MRR@k (Mean Reciprocal Rank)
    
    Args:
        relevance_scores: List of relevance scores (0 or 1)
        k: Number of top results to consider
    
    Returns:
        MRR@k score (0-1)
    """
    if len(relevance_scores) == 0:
        return 0.0
    
    # Take top-k
    relevance_scores = relevance_scores[:k]
    
    # Find first relevant position
    for i, rel in enumerate(relevance_scores):
        if rel == 1:
            return 1.0 / (i + 1)
    
    return 0.0

def calculate_ranking_metrics(scores: np.ndarray, labels: np.ndarray, 
                             query_ids: np.ndarray, k_values: List[int] = [1, 3, 5, 10]) -> Dict[str, float]:
    """
    Calculate ranking metrics (NDCG@k and MRR@k) per query
    
    Args:
        scores: Array of similarity scores
        labels: Array of ground truth labels (0/1)
        query_ids: Array of query identifiers (e.g., CV IDs)
        k_values: List of k values to evaluate
    
    Returns:
        Dictionary with average NDCG@k and MRR@k for each k
    """
    metrics = {f"NDCG@{k}": [] for k in k_values}
    metrics.update({f"MRR@{k}": [] for k in k_values})
    
    # Group by query_id
    unique_queries = np.unique(query_ids)
    
    for query in unique_queries:
        # Get indices for this query
        query_mask = query_ids == query
        query_scores = scores[query_mask]
        query_labels = labels[query_mask]
        
        # Sort by score descending
        sorted_indices = np.argsort(query_scores)[::-1]
        sorted_labels = query_labels[sorted_indices]
        
        # Calculate metrics for each k
        for k in k_values:
            metrics[f"NDCG@{k}"].append(ndcg_at_k(sorted_labels, k))
            metrics[f"MRR@{k}"].append(mrr_at_k(sorted_labels, k))
    
    # Average across queries
    avg_metrics = {}
    for k in k_values:
        avg_metrics[f"NDCG@{k}"] = np.mean(metrics[f"NDCG@{k}"])
        avg_metrics[f"MRR@{k}"] = np.mean(metrics[f"MRR@{k}"])
    
    return avg_metrics

# ============ CONFIGURATION ============

@dataclass
class ModelConfig:
    """Configuration for model training"""
    # TF-IDF config
    tfidf_max_features: int = 500
    tfidf_ngram_range: tuple = (1, 2)
    tfidf_stop_words: str = 'english'
    
    # Word2Vec config
    w2v_vector_size: int = 100
    w2v_window: int = 5
    w2v_min_count: int = 1
    w2v_workers: int = 4
    
    # SBERT config
    sbert_model_name: str = 'all-MiniLM-L6-v2'
    sbert_batch_size: int = 32
    sbert_epochs: int = 3
    sbert_warmup_steps: int = 100
    
    # Classifier config
    classifier_type: str = 'logistic'  # 'logistic', 'random_forest', 'gradient_boosting'
    random_state: int = 42
    
    # Training config
    test_size: float = 0.2
    cv_folds: int = 5
    
    # Ranking metrics config
    ranking_k_values: List[int] = None
    
    def __post_init__(self):
        if self.ranking_k_values is None:
            self.ranking_k_values = [1, 3, 5, 10]
    
    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class ModelMetrics:
    """Model evaluation metrics including ranking metrics"""
    # Classification metrics
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    auc_roc: float
    mcc: float
    confusion_matrix: np.ndarray
    training_time: float
    classification_report: str
    
    # Ranking metrics
    ndcg_1: float = 0.0
    ndcg_3: float = 0.0
    ndcg_5: float = 0.0
    ndcg_10: float = 0.0
    mrr_1: float = 0.0
    mrr_3: float = 0.0
    mrr_5: float = 0.0
    mrr_10: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            'accuracy': self.accuracy,
            'precision': self.precision,
            'recall': self.recall,
            'f1_score': self.f1_score,
            'auc_roc': self.auc_roc,
            'mcc': self.mcc,
            'training_time': self.training_time,
            'confusion_matrix': self.confusion_matrix.tolist(),
            'ndcg_1': self.ndcg_1,
            'ndcg_3': self.ndcg_3,
            'ndcg_5': self.ndcg_5,
            'ndcg_10': self.ndcg_10,
            'mrr_1': self.mrr_1,
            'mrr_3': self.mrr_3,
            'mrr_5': self.mrr_5,
            'mrr_10': self.mrr_10
        }

# ============ DATA PREPROCESSING ============

class DataPreprocessor:
    """Handle data loading and preprocessing"""
    
    def __init__(self):
        self.resume_col = None
        self.job_col = None
        self.label_col = None
        self.cv_id_col = None
        self.jd_id_col = None
        
    def load_data(self, train_path: str, test_path: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Load train and test datasets"""
        logger.info(f"Loading data from {train_path} and {test_path}")
        
        train_df = pd.read_csv(train_path)
        test_df = pd.read_csv(test_path)
        
        logger.info(f"Train set: {len(train_df)} samples")
        logger.info(f"Test set: {len(test_df)} samples")
        logger.info(f"Columns: {train_df.columns.tolist()}")
        
        return train_df, test_df
    
    def identify_columns(self, df: pd.DataFrame) -> None:
        """Automatically identify resume, job, label, and ID columns"""
        # Label column patterns
        label_patterns = ['label', 'match', 'is_match', 'target', 'y']
        for col in df.columns:
            if col.lower() in label_patterns:
                self.label_col = col
                break
        
        if self.label_col is None:
            self.label_col = df.columns[-1]
            logger.warning(f"No label column found, using last column: {self.label_col}")
        
        # Resume/CV column patterns
        resume_patterns = ['resume', 'cv', 'candidate', 'applicant', 'cv_text', 'resume_text']
        for col in df.columns:
            if any(pattern in col.lower() for pattern in resume_patterns):
                self.resume_col = col
                break
        
        # Job column patterns
        job_patterns = ['job', 'position', 'description', 'jd', 'jd_text', 'job_description']
        for col in df.columns:
            if any(pattern in col.lower() for pattern in job_patterns):
                self.job_col = col
                break
        
        # Fallback: assume first two columns are resume/job
        if self.resume_col is None and len(df.columns) >= 2:
            self.resume_col = df.columns[0]
            self.job_col = df.columns[1]
            logger.warning(f"Using first two columns as resume/job: {self.resume_col}, {self.job_col}")
        
        logger.info(f"Identified columns - CV: {self.resume_col}, JD: {self.job_col}, Label: {self.label_col}")
    
    def add_id_columns(self, df: pd.DataFrame, is_train: bool = True) -> pd.DataFrame:
        """Add CV ID and JD ID columns if they don't exist"""
        df_copy = df.copy()
        
        # Add CV IDs
        if 'cv_id' not in df_copy.columns and 'resume_id' not in df_copy.columns:
            prefix = "train" if is_train else "test"
            df_copy['cv_id'] = [f"{prefix}_CV_{i:04d}" for i in range(len(df_copy))]
            logger.info(f"Added dummy CV IDs to {prefix} set")
        elif 'cv_id' not in df_copy.columns:
            df_copy['cv_id'] = df_copy['resume_id']
        
        # Add JD IDs
        if 'jd_id' not in df_copy.columns and 'job_id' not in df_copy.columns:
            df_copy['jd_id'] = [f"JD_{i%500:03d}" for i in range(len(df_copy))]
            logger.info(f"Added dummy JD IDs")
        elif 'jd_id' not in df_copy.columns:
            df_copy['jd_id'] = df_copy['job_id']
        
        # Set ID columns
        self.cv_id_col = 'cv_id'
        self.jd_id_col = 'jd_id'
        
        return df_copy
    
    def prepare_texts(self, df: pd.DataFrame) -> Tuple[List[str], List[str], np.ndarray, np.ndarray, np.ndarray]:
        """Prepare text data for training with IDs"""
        resumes = df[self.resume_col].astype(str).fillna('').tolist()
        jobs = df[self.job_col].astype(str).fillna('').tolist()
        labels = df[self.label_col].values
        cv_ids = df[self.cv_id_col].values
        jd_ids = df[self.jd_id_col].values
        
        logger.info(f"Prepared {len(resumes)} text pairs")
        return resumes, jobs, labels, cv_ids, jd_ids

# ============ FEATURE ENGINEERING ============

class FeatureEngineer:
    """Extract features from text pairs"""
    
    @staticmethod
    def combine_features(emb1: np.ndarray, emb2: np.ndarray) -> np.ndarray:
        """Combine two embeddings into feature vector"""
        return np.concatenate([
            emb1, emb2,
            np.abs(emb1 - emb2),
            emb1 * emb2,
            np.minimum(emb1, emb2),
            np.maximum(emb1, emb2)
        ])
    
    @staticmethod
    def extract_tfidf_features(resumes: List[str], jobs: List[str], 
                               config: ModelConfig) -> Tuple[np.ndarray, TfidfVectorizer]:
        """Extract TF-IDF features"""
        logger.info("Extracting TF-IDF features...")
        
        vectorizer = TfidfVectorizer(
            max_features=config.tfidf_max_features,
            ngram_range=config.tfidf_ngram_range,
            stop_words=config.tfidf_stop_words
        )
        
        # Fit on all texts
        all_texts = resumes + jobs
        vectorizer.fit(all_texts)
        
        # Extract features
        features = []
        for resume, job in tqdm(zip(resumes, jobs), total=len(resumes), desc="TF-IDF features"):
            resume_vec = vectorizer.transform([resume]).toarray()[0]
            job_vec = vectorizer.transform([job]).toarray()[0]
            features.append(FeatureEngineer.combine_features(resume_vec, job_vec))
        
        return np.array(features), vectorizer

# ============ MODEL BASE CLASS ============

class BaseModel:
    """Base class for all models"""
    
    def __init__(self, name: str, config: ModelConfig):
        self.name = name
        self.config = config
        self.model = None
        self.metrics: Optional[ModelMetrics] = None
        self.training_time: float = 0.0
        self.similarity_scores: Optional[np.ndarray] = None
        
    def train(self, X_train: np.ndarray, y_train: np.ndarray) -> None:
        """Train the model"""
        raise NotImplementedError
    
    def predict(self, X_test: np.ndarray) -> np.ndarray:
        """Make predictions"""
        return self.model.predict(X_test)
    
    def predict_proba(self, X_test: np.ndarray) -> np.ndarray:
        """Predict probabilities"""
        if hasattr(self.model, 'predict_proba'):
            return self.model.predict_proba(X_test)
        return None
    
    def get_similarity_scores(self, X_test: np.ndarray) -> np.ndarray:
        """Get similarity/probability scores for ranking"""
        proba = self.predict_proba(X_test)
        if proba is not None:
            return proba[:, 1]  # Probability of positive class
        return self.predict(X_test)  # Fallback to binary predictions
    
    def evaluate(self, X_test: np.ndarray, y_test: np.ndarray, 
                 cv_ids: np.ndarray = None, jd_ids: np.ndarray = None) -> ModelMetrics:
        """Evaluate model performance with classification and ranking metrics"""
        start_time = datetime.now()
        y_pred = self.predict(X_test)
        y_proba = self.predict_proba(X_test)
        
        # Classification metrics
        if y_proba is not None:
            auc = roc_auc_score(y_test, y_proba[:, 1]) if len(np.unique(y_pred)) > 1 else 0.5
        else:
            auc = 0.5
        
        metrics = ModelMetrics(
            accuracy=accuracy_score(y_test, y_pred),
            precision=precision_score(y_test, y_pred, zero_division=0),
            recall=recall_score(y_test, y_pred, zero_division=0),
            f1_score=f1_score(y_test, y_pred, zero_division=0),
            auc_roc=auc,
            mcc=matthews_corrcoef(y_test, y_pred),
            confusion_matrix=confusion_matrix(y_test, y_pred),
            training_time=self.training_time,
            classification_report=classification_report(y_test, y_pred)
        )
        
        # Ranking metrics (if IDs are provided)
        if cv_ids is not None and jd_ids is not None:
            # Get similarity scores for ranking
            similarity_scores = self.get_similarity_scores(X_test)
            
            # Calculate NDCG@k and MRR@k
            ranking_metrics = calculate_ranking_metrics(
                scores=similarity_scores,
                labels=y_test,
                query_ids=cv_ids,
                k_values=self.config.ranking_k_values
            )
            
            # Add ranking metrics to ModelMetrics
            metrics.ndcg_1 = ranking_metrics.get('NDCG@1', 0.0)
            metrics.ndcg_3 = ranking_metrics.get('NDCG@3', 0.0)
            metrics.ndcg_5 = ranking_metrics.get('NDCG@5', 0.0)
            metrics.ndcg_10 = ranking_metrics.get('NDCG@10', 0.0)
            metrics.mrr_1 = ranking_metrics.get('MRR@1', 0.0)
            metrics.mrr_3 = ranking_metrics.get('MRR@3', 0.0)
            metrics.mrr_5 = ranking_metrics.get('MRR@5', 0.0)
            metrics.mrr_10 = ranking_metrics.get('MRR@10', 0.0)
        
        self.metrics = metrics
        return metrics

# ============ CONCRETE MODEL IMPLEMENTATIONS ============

class TFIDFModel(BaseModel):
    """TF-IDF + Logistic Regression model"""
    
    def __init__(self, config: ModelConfig):
        super().__init__("TF-IDF", config)
        self.vectorizer = None
    
    def extract_features(self, resumes: List[str], jobs: List[str]) -> np.ndarray:
        """Extract TF-IDF features"""
        features, self.vectorizer = FeatureEngineer.extract_tfidf_features(
            resumes, jobs, self.config
        )
        return features
    
    def train(self, X_train: np.ndarray, y_train: np.ndarray) -> None:
        start_time = datetime.now()
        
        self.model = LogisticRegression(
            max_iter=1000,
            class_weight='balanced',
            random_state=self.config.random_state
        )
        self.model.fit(X_train, y_train)
        
        self.training_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"{self.name} trained in {self.training_time:.2f}s")

class Word2VecModel(BaseModel):
    """Word2Vec + Random Forest model"""
    
    def __init__(self, config: ModelConfig):
        super().__init__("Word2Vec", config)
        self.w2v_model = None
    
    def _train_word2vec(self, texts: List[str]) -> None:
        """Train Word2Vec model"""
        logger.info("Training Word2Vec model...")
        sentences = [simple_preprocess(text) for text in texts]
        self.w2v_model = Word2Vec(
            sentences,
            vector_size=self.config.w2v_vector_size,
            window=self.config.w2v_window,
            min_count=self.config.w2v_min_count,
            workers=self.config.w2v_workers
        )
    
    def _get_doc_embedding(self, text: str) -> np.ndarray:
        """Get document embedding by averaging word vectors"""
        words = simple_preprocess(text)
        vectors = [self.w2v_model.wv[word] for word in words if word in self.w2v_model.wv]
        if not vectors:
            return np.zeros(self.config.w2v_vector_size)
        return np.mean(vectors, axis=0)
    
    def extract_features(self, resumes: List[str], jobs: List[str]) -> np.ndarray:
        """Extract Word2Vec features"""
        # Train Word2Vec on all texts
        self._train_word2vec(resumes + jobs)
        
        # Extract features
        features = []
        for resume, job in tqdm(zip(resumes, jobs), total=len(resumes), desc="Word2Vec features"):
            resume_vec = self._get_doc_embedding(resume)
            job_vec = self._get_doc_embedding(job)
            features.append(FeatureEngineer.combine_features(resume_vec, job_vec))
        
        return np.array(features)
    
    def train(self, X_train: np.ndarray, y_train: np.ndarray) -> None:
        start_time = datetime.now()
        
        self.model = RandomForestClassifier(
            n_estimators=100,
            class_weight='balanced',
            random_state=self.config.random_state,
            n_jobs=-1
        )
        self.model.fit(X_train, y_train)
        
        self.training_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"{self.name} trained in {self.training_time:.2f}s")

class SBERTModel(BaseModel):
    """SBERT (pre-trained) + Logistic Regression model"""
    
    def __init__(self, config: ModelConfig):
        super().__init__("SBERT", config)
        self.sbert_model = None
    
    def encode(self, texts: List[str]) -> np.ndarray:
        """Encode texts using SBERT"""
        if self.sbert_model is None:
            self.sbert_model = SentenceTransformer(self.config.sbert_model_name)
        
        return self.sbert_model.encode(
            texts,
            batch_size=self.config.sbert_batch_size,
            show_progress_bar=True
        )
    
    def extract_features(self, resumes: List[str], jobs: List[str]) -> np.ndarray:
        """Extract SBERT features"""
        logger.info("Encoding with SBERT...")
        
        resume_embs = self.encode(resumes)
        job_embs = self.encode(jobs)
        
        features = []
        for resume_vec, job_vec in tqdm(zip(resume_embs, job_embs), total=len(resumes), desc="SBERT features"):
            features.append(FeatureEngineer.combine_features(resume_vec, job_vec))
        
        return np.array(features)
    
    def train(self, X_train: np.ndarray, y_train: np.ndarray) -> None:
        start_time = datetime.now()
        
        self.model = LogisticRegression(
            max_iter=1000,
            class_weight='balanced',
            random_state=self.config.random_state
        )
        self.model.fit(X_train, y_train)
        
        self.training_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"{self.name} trained in {self.training_time:.2f}s")

class FineTunedSBERTModel(SBERTModel):
    """Fine-tuned SBERT + Logistic Regression model"""
    
    def __init__(self, config: ModelConfig):
        super().__init__(config)
        self.name = "Fine-tuned SBERT"
    
    def fine_tune(self, resumes: List[str], jobs: List[str], labels: np.ndarray) -> None:
        """Fine-tune SBERT model"""
        logger.info(f"Fine-tuning SBERT for {self.config.sbert_epochs} epochs...")
        
        # Prepare training examples
        train_examples = []
        for resume, job, label in zip(resumes, jobs, labels):
            train_examples.append(InputExample(
                texts=[resume, job],
                label=float(label)
            ))
        
        # Create data loader
        train_dataloader = DataLoader(train_examples, shuffle=True, batch_size=16)
        
        # Fine-tune
        train_loss = losses.CosineSimilarityLoss(self.sbert_model)
        self.sbert_model.fit(
            train_objectives=[(train_dataloader, train_loss)],
            epochs=self.config.sbert_epochs,
            warmup_steps=self.config.sbert_warmup_steps,
            show_progress_bar=True
        )
    
    def train(self, X_train: np.ndarray, y_train: np.ndarray) -> None:
        start_time = datetime.now()
        
        self.model = LogisticRegression(
            max_iter=1000,
            class_weight='balanced',
            random_state=self.config.random_state
        )
        self.model.fit(X_train, y_train)
        
        self.training_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"{self.name} trained in {self.training_time:.2f}s")

# ============ VISUALIZATION ============

class ResultsVisualizer:
    """Create visualizations for model comparison including ranking metrics"""
    
    @staticmethod
    def plot_comparison(results: Dict[str, ModelMetrics], save_path: str = 'output/model_comparison.png'):
        """Create comprehensive comparison plot with ranking metrics"""
        fig, axes = plt.subplots(2, 4, figsize=(20, 10))
        
        # Prepare data
        classification_metrics = ['Accuracy', 'Precision', 'Recall', 'F1-Score', 'AUC-ROC']
        ranking_metrics = ['NDCG@1', 'NDCG@3', 'NDCG@5', 'NDCG@10', 'MRR@1', 'MRR@3', 'MRR@5', 'MRR@10']
        
        metrics_df = pd.DataFrame({
            name: {
                'Accuracy': m.accuracy,
                'Precision': m.precision,
                'Recall': m.recall,
                'F1-Score': m.f1_score,
                'AUC-ROC': m.auc_roc,
                'NDCG@1': m.ndcg_1,
                'NDCG@3': m.ndcg_3,
                'NDCG@5': m.ndcg_5,
                'NDCG@10': m.ndcg_10,
                'MRR@1': m.mrr_1,
                'MRR@3': m.mrr_3,
                'MRR@5': m.mrr_5,
                'MRR@10': m.mrr_10
            }
            for name, m in results.items()
        }).T
        
        # Sort by F1-Score
        metrics_df = metrics_df.sort_values('F1-Score', ascending=False)
        
        # 1. Classification metrics bar plot
        metrics_df[classification_metrics].plot(kind='bar', ax=axes[0, 0])
        axes[0, 0].set_title('Classification Metrics Comparison', fontsize=12, fontweight='bold')
        axes[0, 0].set_xlabel('Model')
        axes[0, 0].set_ylabel('Score')
        axes[0, 0].legend(loc='lower right')
        axes[0, 0].set_xticklabels(metrics_df.index, rotation=45, ha='right')
        axes[0, 0].set_ylim([0, 1])
        
        # 2. NDCG@k comparison
        ndcg_cols = [c for c in metrics_df.columns if c.startswith('NDCG')]
        metrics_df[ndcg_cols].plot(kind='bar', ax=axes[0, 1])
        axes[0, 1].set_title('NDCG@k Comparison', fontsize=12, fontweight='bold')
        axes[0, 1].set_xlabel('Model')
        axes[0, 1].set_ylabel('NDCG Score')
        axes[0, 1].legend(loc='lower right')
        axes[0, 1].set_xticklabels(metrics_df.index, rotation=45, ha='right')
        axes[0, 1].set_ylim([0, 1])
        
        # 3. MRR@k comparison
        mrr_cols = [c for c in metrics_df.columns if c.startswith('MRR')]
        metrics_df[mrr_cols].plot(kind='bar', ax=axes[0, 2])
        axes[0, 2].set_title('MRR@k Comparison', fontsize=12, fontweight='bold')
        axes[0, 2].set_xlabel('Model')
        axes[0, 2].set_ylabel('MRR Score')
        axes[0, 2].legend(loc='lower right')
        axes[0, 2].set_xticklabels(metrics_df.index, rotation=45, ha='right')
        axes[0, 2].set_ylim([0, 1])
        
        # 4. F1-Score barh
        f1_scores = metrics_df['F1-Score']
        bars = axes[0, 3].barh(metrics_df.index, f1_scores, color='skyblue')
        axes[0, 3].set_title('F1-Score Comparison', fontsize=12, fontweight='bold')
        axes[0, 3].set_xlabel('F1-Score')
        for bar, score in zip(bars, f1_scores):
            axes[0, 3].text(score, bar.get_y() + bar.get_height()/2, f'{score:.3f}', 
                           va='center', ha='left', fontsize=9)
        
        # 5. Training time
        train_times = [results[name].training_time for name in metrics_df.index]
        bars = axes[1, 0].barh(metrics_df.index, train_times, color='lightcoral')
        axes[1, 0].set_title('Training Time (seconds)', fontsize=12, fontweight='bold')
        axes[1, 0].set_xlabel('Time (s)')
        for bar, time in zip(bars, train_times):
            axes[1, 0].text(time, bar.get_y() + bar.get_height()/2, f'{time:.1f}s', 
                           va='center', ha='left', fontsize=9)
        
        # 6. NDCG@10 vs F1-Score scatter
        axes[1, 1].scatter(metrics_df['F1-Score'], metrics_df['NDCG@10'], s=100, alpha=0.6)
        for idx, row in metrics_df.iterrows():
            axes[1, 1].annotate(idx, (row['F1-Score'], row['NDCG@10']), fontsize=8)
        axes[1, 1].set_xlabel('F1-Score')
        axes[1, 1].set_ylabel('NDCG@10')
        axes[1, 1].set_title('F1-Score vs NDCG@10', fontsize=12, fontweight='bold')
        axes[1, 1].grid(True, alpha=0.3)
        
        # 7. Ranking metrics heatmap
        sns.heatmap(metrics_df[ranking_metrics], annot=True, fmt='.3f', cmap='YlOrRd', 
                   ax=axes[1, 2], cbar_kws={'label': 'Score'})
        axes[1, 2].set_title('Ranking Metrics Heatmap', fontsize=12, fontweight='bold')
        
        # 8. All metrics heatmap
        sns.heatmap(metrics_df[classification_metrics + ranking_metrics], 
                   annot=True, fmt='.3f', cmap='YlOrRd', 
                   ax=axes[1, 3], cbar_kws={'label': 'Score'})
        axes[1, 3].set_title('Complete Metrics Heatmap', fontsize=12, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        logger.info(f"Saved comparison plot to {save_path}")
        plt.close()

# ============ MAIN PIPELINE ============

class JobMatchingPipeline:
    """Main pipeline for training and evaluating job matching models"""
    
    def __init__(self, config: ModelConfig = None):
        self.config = config or ModelConfig()
        self.preprocessor = DataPreprocessor()
        self.results: Dict[str, ModelMetrics] = {}
        self.models: Dict[str, BaseModel] = {}
        
        # Create output directories
        Path('output').mkdir(exist_ok=True)
        Path('output/models').mkdir(exist_ok=True)
    
    def run(self, train_path: str, test_path: str) -> Dict[str, ModelMetrics]:
        """Run complete training and evaluation pipeline"""
        logger.info("="*80)
        logger.info("STARTING JOB MATCHING MODEL TRAINING PIPELINE")
        logger.info("="*80)
        
        # 1. Load data
        train_df, test_df = self.preprocessor.load_data(train_path, test_path)
        self.preprocessor.identify_columns(train_df)
        
        # 2. Add ID columns
        train_df = self.preprocessor.add_id_columns(train_df, is_train=True)
        test_df = self.preprocessor.add_id_columns(test_df, is_train=False)
        
        # 3. Prepare texts with IDs
        train_resumes, train_jobs, train_labels, train_cv_ids, train_jd_ids = self.preprocessor.prepare_texts(train_df)
        test_resumes, test_jobs, test_labels, test_cv_ids, test_jd_ids = self.preprocessor.prepare_texts(test_df)
        
        logger.info(f"Class distribution - Train: {np.bincount(train_labels)}")
        logger.info(f"Class distribution - Test: {np.bincount(test_labels)}")
        logger.info(f"Unique CVs in test: {len(np.unique(test_cv_ids))}")
        
        # 4. Train TF-IDF model
        logger.info("\n" + "="*60)
        logger.info("Training TF-IDF Model...")
        tfidf_model = TFIDFModel(self.config)
        X_train_tfidf = tfidf_model.extract_features(train_resumes, train_jobs)
        X_test_tfidf = tfidf_model.extract_features(test_resumes, test_jobs)
        tfidf_model.train(X_train_tfidf, train_labels)
        metrics_tfidf = tfidf_model.evaluate(X_test_tfidf, test_labels, test_cv_ids, test_jd_ids)
        self.results['TF-IDF'] = metrics_tfidf
        self.models['TF-IDF'] = tfidf_model
        
        # 5. Train Word2Vec model
        logger.info("\n" + "="*60)
        logger.info("Training Word2Vec Model...")
        w2v_model = Word2VecModel(self.config)
        X_train_w2v = w2v_model.extract_features(train_resumes, train_jobs)
        X_test_w2v = w2v_model.extract_features(test_resumes, test_jobs)
        w2v_model.train(X_train_w2v, train_labels)
        metrics_w2v = w2v_model.evaluate(X_test_w2v, test_labels, test_cv_ids, test_jd_ids)
        self.results['Word2Vec'] = metrics_w2v
        self.models['Word2Vec'] = w2v_model
        
        # 6. Train SBERT model
        logger.info("\n" + "="*60)
        logger.info("Training SBERT Model...")
        sbert_model = SBERTModel(self.config)
        X_train_sbert = sbert_model.extract_features(train_resumes, train_jobs)
        X_test_sbert = sbert_model.extract_features(test_resumes, test_jobs)
        sbert_model.train(X_train_sbert, train_labels)
        metrics_sbert = sbert_model.evaluate(X_test_sbert, test_labels, test_cv_ids, test_jd_ids)
        self.results['SBERT'] = metrics_sbert
        self.models['SBERT'] = sbert_model
        
        # 7. Train Fine-tuned SBERT model (optional)
        logger.info("\n" + "="*60)
        logger.info("Training Fine-tuned SBERT Model (may take several minutes)...")
        finetuned_model = FineTunedSBERTModel(self.config)
        finetuned_model.sbert_model = SentenceTransformer(self.config.sbert_model_name)
        finetuned_model.fine_tune(train_resumes, train_jobs, train_labels)
        X_train_finetuned = finetuned_model.extract_features(train_resumes, train_jobs)
        X_test_finetuned = finetuned_model.extract_features(test_resumes, test_jobs)
        finetuned_model.train(X_train_finetuned, train_labels)
        metrics_finetuned = finetuned_model.evaluate(X_test_finetuned, test_labels, test_cv_ids, test_jd_ids)
        self.results['Fine-tuned SBERT'] = metrics_finetuned
        self.models['Fine-tuned SBERT'] = finetuned_model
        
        return self.results
    
    def save_results(self, output_dir: str = 'output'):
        """Save all results and models"""
        # Save model metrics
        metrics_df = pd.DataFrame({
            name: m.to_dict() for name, m in self.results.items()
        }).T
        
        metrics_df.to_csv(f'{output_dir}/model_metrics.csv')
        logger.info(f"Saved metrics to {output_dir}/model_metrics.csv")
        
        # Save models
        for name, model in self.models.items():
            model_path = f'{output_dir}/models/{name.replace(" ", "_")}.pkl'
            with open(model_path, 'wb') as f:
                pickle.dump(model, f)
            logger.info(f"Saved model: {model_path}")
        
        # Save configuration
        with open(f'{output_dir}/config.json', 'w') as f:
            json.dump(self.config.to_dict(), f, indent=2)
        
        # Create visualization
        visualizer = ResultsVisualizer()
        visualizer.plot_comparison(self.results, f'{output_dir}/model_comparison.png')
        
        # Generate report
        self._generate_report(metrics_df, output_dir)
    
    def _generate_report(self, metrics_df: pd.DataFrame, output_dir: str):
        """Generate detailed evaluation report with ranking metrics"""
        best_f1_model = metrics_df['f1_score'].idxmax()
        best_f1 = metrics_df.loc[best_f1_model, 'f1_score']
        
        best_ndcg_model = metrics_df['ndcg_10'].idxmax()
        best_ndcg = metrics_df.loc[best_ndcg_model, 'ndcg_10']
        
        report = f"""
{'='*80}
JOB MATCHING MODEL EVALUATION REPORT
{'='*80}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Configuration: {json.dumps(self.config.to_dict(), indent=2)}

{'='*80}
CLASSIFICATION METRICS
{'='*80}
{metrics_df[['accuracy', 'precision', 'recall', 'f1_score', 'auc_roc', 'training_time']].round(4).to_string()}

{'='*80}
RANKING METRICS (NDCG@k & MRR@k)
{'='*80}
{metrics_df[[c for c in metrics_df.columns if c.startswith(('ndcg', 'mrr'))]].round(4).to_string()}

{'='*80}
BEST MODELS
{'='*80}
Best by F1-Score:
- Model: {best_f1_model}
- F1-Score: {best_f1:.4f}
- Accuracy: {metrics_df.loc[best_f1_model, 'accuracy']:.4f}
- Precision: {metrics_df.loc[best_f1_model, 'precision']:.4f}
- Recall: {metrics_df.loc[best_f1_model, 'recall']:.4f}
- AUC-ROC: {metrics_df.loc[best_f1_model, 'auc_roc']:.4f}
- NDCG@10: {metrics_df.loc[best_f1_model, 'ndcg_10']:.4f}

Best by NDCG@10:
- Model: {best_ndcg_model}
- NDCG@10: {best_ndcg:.4f}
- F1-Score: {metrics_df.loc[best_ndcg_model, 'f1_score']:.4f}

{'='*80}
RECOMMENDATIONS
{'='*80}
1. {'✅ Production ready' if best_f1 > 0.7 else '⚠️ Need more data for production'}
2. {'✅ Fine-tuning improved performance' if 'Fine-tuned SBERT' in metrics_df.index and metrics_df.loc['Fine-tuned SBERT', 'f1_score'] > metrics_df.loc['SBERT', 'f1_score'] else "⚠️ Fine-tuning didn't help"}
3. {'✅ Good ranking performance' if best_ndcg > 0.7 else '⚠️ Ranking needs improvement'}
4. {'✅ Consider ensemble methods' if best_f1 < 0.8 else '✅ Single model is sufficient'}

{'='*80}
INTERPRETATION OF RANKING METRICS
{'='*80}
- NDCG@k: Measures ranking quality (1.0 = perfect ranking)
- MRR@k: Measures how early first relevant item appears
- Higher scores = better ranking performance

{'='*80}
FILES GENERATED
{'='*80}
1. {output_dir}/model_metrics.csv - Performance metrics
2. {output_dir}/model_comparison.png - Visualization
3. {output_dir}/models/ - Saved models
4. {output_dir}/config.json - Training configuration
5. {output_dir}/training.log - Training logs

{'='*80}
"""
        
        with open(f'{output_dir}/evaluation_report.txt', 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"Report saved to {output_dir}/evaluation_report.txt")
        print(report)

# ============ MAIN EXECUTION ============

def main():
    """Main entry point"""
    # Configuration
    config = ModelConfig(
        tfidf_max_features=500,
        sbert_epochs=3,
        classifier_type='logistic',
        ranking_k_values=[1, 3, 5, 10]
    )
    
    # Paths - adjust these to your actual file paths
    TRAIN_PATH = '../data/processed/train_dataset.csv'
    TEST_PATH = '../data/processed/test_dataset.csv'
    
    # Alternative paths if files not found
    if not os.path.exists(TRAIN_PATH):
        # Try current directory
        TRAIN_PATH = 'train_dataset.csv'
        TEST_PATH = 'test_dataset.csv'
    
    # Check if files exist
    if not os.path.exists(TRAIN_PATH):
        logger.error(f"Train file not found: {TRAIN_PATH}")
        logger.info("Looking for CSV files in current directory...")
        
        # List all CSV files in current directory
        csv_files = [f for f in os.listdir('.') if f.endswith('.csv')]
        if csv_files:
            logger.info(f"Available CSV files: {csv_files}")
            if len(csv_files) >= 2:
                TRAIN_PATH = csv_files[0]
                TEST_PATH = csv_files[1]
                logger.info(f"Using {TRAIN_PATH} as train and {TEST_PATH} as test")
            else:
                logger.error("Need both train and test CSV files")
                return
        else:
            logger.error("No CSV files found in current directory")
            return
    
    # Run pipeline
    pipeline = JobMatchingPipeline(config)
    
    try:
        results = pipeline.run(TRAIN_PATH, TEST_PATH)
        pipeline.save_results()
        
        logger.info("\n" + "="*80)
        logger.info("✅ PIPELINE COMPLETED SUCCESSFULLY!")
        logger.info("="*80)
        
        # Print quick summary
        print("\n" + "="*60)
        print("QUICK SUMMARY")
        print("="*60)
        for name, metrics in results.items():
            print(f"{name:20s} - F1: {metrics.f1_score:.4f}, NDCG@10: {metrics.ndcg_10:.4f}, Time: {metrics.training_time:.1f}s")
        
    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    main()