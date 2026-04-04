"""
JOB MATCHING MODEL TRAINING PIPELINE - PRODUCTION READY
Author: Professional ML Engineer
Version: 2.0.0
Description: Production-grade training pipeline for job matching models
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
    
    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class ModelMetrics:
    """Model evaluation metrics"""
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    auc_roc: float
    mcc: float
    confusion_matrix: np.ndarray
    training_time: float
    classification_report: str
    
    def to_dict(self) -> dict:
        return {
            'accuracy': self.accuracy,
            'precision': self.precision,
            'recall': self.recall,
            'f1_score': self.f1_score,
            'auc_roc': self.auc_roc,
            'mcc': self.mcc,
            'training_time': self.training_time,
            'confusion_matrix': self.confusion_matrix.tolist()
        }

# ============ DATA PREPROCESSING ============

class DataPreprocessor:
    """Handle data loading and preprocessing"""
    
    def __init__(self):
        self.resume_col = None
        self.job_col = None
        self.label_col = None
        
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
        """Automatically identify resume, job, and label columns"""
        # Label column patterns
        label_patterns = ['label', 'match', 'is_match', 'target', 'y']
        for col in df.columns:
            if col.lower() in label_patterns:
                self.label_col = col
                break
        
        if self.label_col is None:
            self.label_col = df.columns[-1]  # Assume last column is label
            logger.warning(f"No label column found, using last column: {self.label_col}")
        
        # Resume column patterns
        resume_patterns = ['resume', 'cv', 'candidate', 'applicant', 'text']
        for col in df.columns:
            if any(pattern in col.lower() for pattern in resume_patterns):
                self.resume_col = col
                break
        
        # Job column patterns
        job_patterns = ['job', 'position', 'description', 'jd', 'posting']
        for col in df.columns:
            if any(pattern in col.lower() for pattern in job_patterns):
                self.job_col = col
                break
        
        # Fallback: assume first two columns
        if self.resume_col is None and len(df.columns) >= 2:
            self.resume_col = df.columns[0]
            self.job_col = df.columns[1]
            logger.warning(f"Using first two columns as resume/job: {self.resume_col}, {self.job_col}")
        
        logger.info(f"Identified columns - Resume: {self.resume_col}, Job: {self.job_col}, Label: {self.label_col}")
    
    def prepare_texts(self, df: pd.DataFrame) -> Tuple[List[str], List[str], np.ndarray]:
        """Prepare text data for training"""
        resumes = df[self.resume_col].astype(str).fillna('').tolist()
        jobs = df[self.job_col].astype(str).fillna('').tolist()
        labels = df[self.label_col].values
        
        logger.info(f"Prepared {len(resumes)} text pairs")
        return resumes, jobs, labels

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
    
    def evaluate(self, X_test: np.ndarray, y_test: np.ndarray) -> ModelMetrics:
        """Evaluate model performance"""
        start_time = datetime.now()
        y_pred = self.predict(X_test)
        y_proba = self.predict_proba(X_test)
        
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
        
        # Note: X_train is not used here because fine-tuning uses raw texts
        # This is a limitation - in production, you'd pass raw texts separately
        
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
    """Create visualizations for model comparison"""
    
    @staticmethod
    def plot_comparison(results: Dict[str, ModelMetrics], save_path: str = 'output/model_comparison.png'):
        """Create comprehensive comparison plot"""
        fig, axes = plt.subplots(2, 3, figsize=(15, 10))
        
        # Prepare data
        metrics_df = pd.DataFrame({
            name: {
                'Accuracy': m.accuracy,
                'Precision': m.precision,
                'Recall': m.recall,
                'F1-Score': m.f1_score,
                'AUC-ROC': m.auc_roc
            }
            for name, m in results.items()
        }).T
        
        # Sort by F1-Score
        metrics_df = metrics_df.sort_values('F1-Score', ascending=False)
        
        # 1. Bar plot
        metrics_df.plot(kind='bar', ax=axes[0, 0])
        axes[0, 0].set_title('Model Performance Comparison', fontsize=12, fontweight='bold')
        axes[0, 0].set_xlabel('Model')
        axes[0, 0].set_ylabel('Score')
        axes[0, 0].legend(loc='lower right')
        axes[0, 0].set_xticklabels(metrics_df.index, rotation=45, ha='right')
        
        # 2. AUC-ROC barh
        auc_scores = metrics_df['AUC-ROC']
        bars = axes[0, 1].barh(metrics_df.index, auc_scores, color='skyblue')
        axes[0, 1].set_title('AUC-ROC Scores', fontsize=12, fontweight='bold')
        axes[0, 1].set_xlabel('AUC-ROC')
        for bar, score in zip(bars, auc_scores):
            axes[0, 1].text(score, bar.get_y() + bar.get_height()/2, f'{score:.3f}', 
                           va='center', ha='left', fontsize=9)
        
        # 3. Training time
        train_times = [results[name].training_time for name in metrics_df.index]
        bars = axes[0, 2].barh(metrics_df.index, train_times, color='lightcoral')
        axes[0, 2].set_title('Training Time (seconds)', fontsize=12, fontweight='bold')
        axes[0, 2].set_xlabel('Time (s)')
        for bar, time in zip(bars, train_times):
            axes[0, 2].text(time, bar.get_y() + bar.get_height()/2, f'{time:.1f}s', 
                           va='center', ha='left', fontsize=9)
        
        # 4. Confusion matrices for top 2 models
        top_models = metrics_df.head(2).index
        for idx, model in enumerate(top_models):
            cm = results[model].confusion_matrix
            sns.heatmap(cm, annot=True, fmt='d', ax=axes[1, idx], cmap='Blues', cbar=False)
            axes[1, idx].set_title(f'{model} - Confusion Matrix', fontsize=11, fontweight='bold')
            axes[1, idx].set_xlabel('Predicted')
            axes[1, idx].set_ylabel('Actual')
        
        # 5. Metrics heatmap
        sns.heatmap(metrics_df, annot=True, fmt='.3f', cmap='YlOrRd', 
                   ax=axes[1, 2], cbar_kws={'label': 'Score'})
        axes[1, 2].set_title('Metrics Heatmap', fontsize=12, fontweight='bold')
        
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
        
        # 1. Load and preprocess data
        train_df, test_df = self.preprocessor.load_data(train_path, test_path)
        self.preprocessor.identify_columns(train_df)
        
        train_resumes, train_jobs, train_labels = self.preprocessor.prepare_texts(train_df)
        test_resumes, test_jobs, test_labels = self.preprocessor.prepare_texts(test_df)
        
        logger.info(f"Class distribution - Train: {np.bincount(train_labels)}")
        logger.info(f"Class distribution - Test: {np.bincount(test_labels)}")
        
        # 2. Train TF-IDF model
        logger.info("\n" + "="*60)
        tfidf_model = TFIDFModel(self.config)
        X_train_tfidf = tfidf_model.extract_features(train_resumes, train_jobs)
        X_test_tfidf = tfidf_model.extract_features(test_resumes, test_jobs)
        tfidf_model.train(X_train_tfidf, train_labels)
        metrics_tfidf = tfidf_model.evaluate(X_test_tfidf, test_labels)
        self.results['TF-IDF'] = metrics_tfidf
        self.models['TF-IDF'] = tfidf_model
        
        # 3. Train Word2Vec model
        logger.info("\n" + "="*60)
        w2v_model = Word2VecModel(self.config)
        X_train_w2v = w2v_model.extract_features(train_resumes, train_jobs)
        X_test_w2v = w2v_model.extract_features(test_resumes, test_jobs)
        w2v_model.train(X_train_w2v, train_labels)
        metrics_w2v = w2v_model.evaluate(X_test_w2v, test_labels)
        self.results['Word2Vec'] = metrics_w2v
        self.models['Word2Vec'] = w2v_model
        
        # 4. Train SBERT model
        logger.info("\n" + "="*60)
        sbert_model = SBERTModel(self.config)
        X_train_sbert = sbert_model.extract_features(train_resumes, train_jobs)
        X_test_sbert = sbert_model.extract_features(test_resumes, test_jobs)
        sbert_model.train(X_train_sbert, train_labels)
        metrics_sbert = sbert_model.evaluate(X_test_sbert, test_labels)
        self.results['SBERT'] = metrics_sbert
        self.models['SBERT'] = sbert_model
        
        # 5. Train Fine-tuned SBERT model (optional, time-consuming)
        logger.info("\n" + "="*60)
        logger.info("Fine-tuned SBERT may take several minutes...")
        finetuned_model = FineTunedSBERTModel(self.config)
        # Note: For fine-tuned SBERT, we need to fine-tune first then extract features
        finetuned_model.sbert_model = SentenceTransformer(self.config.sbert_model_name)
        finetuned_model.fine_tune(train_resumes, train_jobs, train_labels)
        X_train_finetuned = finetuned_model.extract_features(train_resumes, train_jobs)
        X_test_finetuned = finetuned_model.extract_features(test_resumes, test_jobs)
        finetuned_model.train(X_train_finetuned, train_labels)
        metrics_finetuned = finetuned_model.evaluate(X_test_finetuned, test_labels)
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
        """Generate detailed evaluation report"""
        best_model = metrics_df['f1_score'].idxmax()
        best_f1 = metrics_df.loc[best_model, 'f1_score']
        
        report = f"""
{'='*80}
JOB MATCHING MODEL EVALUATION REPORT
{'='*80}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Configuration: {json.dumps(self.config.to_dict(), indent=2)}

{'='*80}
MODEL PERFORMANCE SUMMARY
{'='*80}
{metrics_df[['accuracy', 'precision', 'recall', 'f1_score', 'auc_roc', 'training_time']].round(4).to_string()}

{'='*80}
BEST MODEL
{'='*80}
Model: {best_model}
- F1-Score: {best_f1:.4f}
- Accuracy: {metrics_df.loc[best_model, 'accuracy']:.4f}
- Precision: {metrics_df.loc[best_model, 'precision']:.4f}
- Recall: {metrics_df.loc[best_model, 'recall']:.4f}
- AUC-ROC: {metrics_df.loc[best_model, 'auc_roc']:.4f}

{'='*80}
RECOMMENDATIONS
{'='*80}
1. {'✅ Production ready' if best_f1 > 0.7 else '⚠️ Need more data for production'}
2. {'✅ Fine-tuning improved performance' if 'Fine-tuned SBERT' in metrics_df.index and metrics_df.loc['Fine-tuned SBERT', 'f1_score'] > metrics_df.loc['SBERT', 'f1_score'] else "⚠️ Fine-tuning didn't help"}
3. {'✅ Consider ensemble methods' if best_f1 < 0.8 else '✅ Single model is sufficient'}

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
        classifier_type='logistic'
    )
    
    # Paths
    TRAIN_PATH = '../data/processed/train_dataset.csv'
    TEST_PATH = '../data/processed/test_dataset.csv'
    
    # Check if files exist
    if not os.path.exists(TRAIN_PATH):
        logger.error(f"Train file not found: {TRAIN_PATH}")
        logger.info("Please run data preparation first")
        return
    
    if not os.path.exists(TEST_PATH):
        logger.error(f"Test file not found: {TEST_PATH}")
        return
    
    # Run pipeline
    pipeline = JobMatchingPipeline(config)
    
    try:
        results = pipeline.run(TRAIN_PATH, TEST_PATH)
        pipeline.save_results()
        
        logger.info("\n" + "="*80)
        logger.info("✅ PIPELINE COMPLETED SUCCESSFULLY!")
        logger.info("="*80)
        
    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}")
        raise

if __name__ == "__main__":
    main()