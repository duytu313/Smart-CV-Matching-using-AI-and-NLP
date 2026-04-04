"""
Evaluation Service for the Job Recommendation System.
Implements standard information retrieval metrics for recommendation quality assessment.
"""

import numpy as np
from typing import List, Dict, Set, Optional
from dataclasses import dataclass


@dataclass
class EvaluationResult:
    """Results of evaluation metrics."""
    precision_at_k: float
    recall_at_k: float
    f1_at_k: float
    ndcg_at_k: float
    map_at_k: float
    mrr: float
    hit_rate: float
    k: int
    num_relevant: int
    num_recommended: int


class EvaluationService:
    """
    Service for evaluating recommendation quality.
    Implements Precision@K, Recall@K, F1@K, NDCG@K, MAP, MRR, and Hit Rate.
    """
    
    @staticmethod
    def precision_at_k(
        recommended: List[int],
        relevant: Set[int],
        k: int
    ) -> float:
        """
        Calculate Precision@K.
        
        Precision@K = (Number of relevant items in top-K) / K
        
        Args:
            recommended: List of recommended item IDs (ordered by relevance)
            relevant: Set of relevant item IDs
            k: Number of recommendations to consider
            
        Returns:
            Precision@K score between 0 and 1
        """
        if k <= 0:
            return 0.0
        
        top_k = recommended[:k]
        relevant_in_top_k = sum(1 for item in top_k if item in relevant)
        
        return relevant_in_top_k / k
    
    @staticmethod
    def recall_at_k(
        recommended: List[int],
        relevant: Set[int],
        k: int
    ) -> float:
        """
        Calculate Recall@K.
        
        Recall@K = (Number of relevant items in top-K) / (Total relevant items)
        
        Args:
            recommended: List of recommended item IDs (ordered by relevance)
            relevant: Set of relevant item IDs
            k: Number of recommendations to consider
            
        Returns:
            Recall@K score between 0 and 1
        """
        if not relevant:
            return 0.0
        
        top_k = recommended[:k]
        relevant_in_top_k = sum(1 for item in top_k if item in relevant)
        
        return relevant_in_top_k / len(relevant)
    
    @staticmethod
    def f1_at_k(
        recommended: List[int],
        relevant: Set[int],
        k: int
    ) -> float:
        """
        Calculate F1@K (harmonic mean of Precision@K and Recall@K).
        
        F1@K = 2 * (Precision@K * Recall@K) / (Precision@K + Recall@K)
        
        Args:
            recommended: List of recommended item IDs (ordered by relevance)
            relevant: Set of relevant item IDs
            k: Number of recommendations to consider
            
        Returns:
            F1@K score between 0 and 1
        """
        precision = EvaluationService.precision_at_k(recommended, relevant, k)
        recall = EvaluationService.recall_at_k(recommended, relevant, k)
        
        if precision + recall == 0:
            return 0.0
        
        return 2 * (precision * recall) / (precision + recall)
    
    @staticmethod
    def dcg_at_k(
        recommended: List[int],
        relevance_scores: Dict[int, float],
        k: int
    ) -> float:
        """
        Calculate Discounted Cumulative Gain at K.
        
        DCG@K = sum(relevance_i / log2(i + 1)) for i in 1..K
        
        Args:
            recommended: List of recommended item IDs (ordered by relevance)
            relevance_scores: Dictionary mapping item IDs to relevance scores
            k: Number of recommendations to consider
            
        Returns:
            DCG@K score
        """
        dcg = 0.0
        top_k = recommended[:k]
        
        for i, item_id in enumerate(top_k, start=1):
            relevance = relevance_scores.get(item_id, 0.0)
            dcg += relevance / np.log2(i + 1)
        
        return dcg
    
    @staticmethod
    def ndcg_at_k(
        recommended: List[int],
        relevance_scores: Dict[int, float],
        k: int
    ) -> float:
        """
        Calculate Normalized Discounted Cumulative Gain at K.
        
        NDCG@K = DCG@K / IDCG@K
        
        where IDCG@K is the ideal DCG (with perfect ranking)
        
        Args:
            recommended: List of recommended item IDs (ordered by relevance)
            relevance_scores: Dictionary mapping item IDs to relevance scores
            k: Number of recommendations to consider
            
        Returns:
            NDCG@K score between 0 and 1
        """
        # Calculate actual DCG
        dcg = EvaluationService.dcg_at_k(recommended, relevance_scores, k)
        
        # Calculate ideal DCG (perfect ranking)
        sorted_relevances = sorted(relevance_scores.values(), reverse=True)[:k]
        idcg = sum(rel / np.log2(i + 2) for i, rel in enumerate(sorted_relevances))
        
        if idcg == 0:
            return 0.0
        
        return dcg / idcg
    
    @staticmethod
    def ndcg_at_k_binary(
        recommended: List[int],
        relevant: Set[int],
        k: int
    ) -> float:
        """
        Calculate NDCG@K with binary relevance (relevant = 1, not relevant = 0).
        
        Args:
            recommended: List of recommended item IDs (ordered by relevance)
            relevant: Set of relevant item IDs
            k: Number of recommendations to consider
            
        Returns:
            NDCG@K score between 0 and 1
        """
        # Convert to relevance scores (1 for relevant, 0 for not relevant)
        relevance_scores = {item_id: 1.0 for item_id in relevant}
        return EvaluationService.ndcg_at_k(recommended, relevance_scores, k)
    
    @staticmethod
    def average_precision(
        recommended: List[int],
        relevant: Set[int]
    ) -> float:
        """
        Calculate Average Precision for a single query.
        
        AP = (1/|relevant|) * sum(Precision@k * rel(k)) for k in 1..n
        
        Args:
            recommended: List of recommended item IDs (ordered by relevance)
            relevant: Set of relevant item IDs
            
        Returns:
            Average Precision score
        """
        if not relevant:
            return 0.0
        
        ap = 0.0
        relevant_count = 0
        
        for i, item_id in enumerate(recommended, start=1):
            if item_id in relevant:
                relevant_count += 1
                ap += relevant_count / i
        
        return ap / len(relevant)
    
    @staticmethod
    def map_at_k(
        all_recommended: List[List[int]],
        all_relevant: List[Set[int]],
        k: int
    ) -> float:
        """
        Calculate Mean Average Precision at K across multiple queries.
        
        MAP@K = mean(AP@K) for all queries
        
        Args:
            all_recommended: List of recommendation lists (one per query)
            all_relevant: List of relevant item sets (one per query)
            k: Number of recommendations to consider
            
        Returns:
            MAP@K score
        """
        if not all_recommended:
            return 0.0
        
        aps = []
        for recommended, relevant in zip(all_recommended, all_relevant):
            # Truncate recommendations to K
            truncated = recommended[:k]
            ap = EvaluationService.average_precision(truncated, relevant)
            aps.append(ap)
        
        return np.mean(aps)
    
    @staticmethod
    def mrr(
        all_recommended: List[List[int]],
        all_relevant: List[Set[int]]
    ) -> float:
        """
        Calculate Mean Reciprocal Rank.
        
        MRR = mean(1 / rank_of_first_relevant_item) for all queries
        
        Args:
            all_recommended: List of recommendation lists (one per query)
            all_relevant: List of relevant item sets (one per query)
            
        Returns:
            MRR score
        """
        if not all_recommended:
            return 0.0
        
        reciprocal_ranks = []
        
        for recommended, relevant in zip(all_recommended, all_relevant):
            for i, item_id in enumerate(recommended, start=1):
                if item_id in relevant:
                    reciprocal_ranks.append(1 / i)
                    break
            else:
                reciprocal_ranks.append(0.0)
        
        return np.mean(reciprocal_ranks)
    
    @staticmethod
    def hit_rate_at_k(
        all_recommended: List[List[int]],
        all_relevant: List[Set[int]],
        k: int
    ) -> float:
        """
        Calculate Hit Rate at K (also known as Recall@K for binary relevance).
        
        Hit Rate@K = (Number of queries with at least one relevant item in top-K) / (Total queries)
        
        Args:
            all_recommended: List of recommendation lists (one per query)
            all_relevant: List of relevant item sets (one per query)
            k: Number of recommendations to consider
            
        Returns:
            Hit Rate@K score
        """
        if not all_recommended:
            return 0.0
        
        hits = 0
        
        for recommended, relevant in zip(all_recommended, all_relevant):
            top_k = set(recommended[:k])
            if top_k & relevant:  # If there's any intersection
                hits += 1
        
        return hits / len(all_recommended)
    
    @classmethod
    def evaluate_recommendations(
        cls,
        recommended: List[int],
        relevant: Set[int],
        k: int,
        relevance_scores: Optional[Dict[int, float]] = None
    ) -> EvaluationResult:
        """
        Comprehensive evaluation of a single recommendation list.
        
        Args:
            recommended: List of recommended item IDs (ordered by relevance)
            relevant: Set of relevant item IDs
            k: Number of recommendations to consider
            relevance_scores: Optional graded relevance scores
            
        Returns:
            EvaluationResult with all metrics
        """
        precision = cls.precision_at_k(recommended, relevant, k)
        recall = cls.recall_at_k(recommended, relevant, k)
        f1 = cls.f1_at_k(recommended, relevant, k)
        
        if relevance_scores:
            ndcg = cls.ndcg_at_k(recommended, relevance_scores, k)
        else:
            ndcg = cls.ndcg_at_k_binary(recommended, relevant, k)
        
        ap = cls.average_precision(recommended[:k], relevant)
        
        # MRR for single query
        mrr_score = 0.0
        for i, item_id in enumerate(recommended[:k], start=1):
            if item_id in relevant:
                mrr_score = 1 / i
                break
        
        # Hit rate for single query
        hit = 1.0 if set(recommended[:k]) & relevant else 0.0
        
        return EvaluationResult(
            precision_at_k=round(precision, 4),
            recall_at_k=round(recall, 4),
            f1_at_k=round(f1, 4),
            ndcg_at_k=round(ndcg, 4),
            map_at_k=round(ap, 4),
            mrr=round(mrr_score, 4),
            hit_rate=round(hit, 4),
            k=k,
            num_relevant=len(relevant),
            num_recommended=len(recommended[:k])
        )
    
    @classmethod
    def evaluate_batch(
        cls,
        all_recommended: List[List[int]],
        all_relevant: List[Set[int]],
        k: int
    ) -> Dict[str, float]:
        """
        Evaluate recommendations across multiple queries.
        
        Args:
            all_recommended: List of recommendation lists
            all_relevant: List of relevant item sets
            k: Number of recommendations to consider
            
        Returns:
            Dictionary with averaged metrics
        """
        n = len(all_recommended)
        if n == 0:
            return {
                'precision_at_k': 0.0,
                'recall_at_k': 0.0,
                'f1_at_k': 0.0,
                'ndcg_at_k': 0.0,
                'map_at_k': 0.0,
                'mrr': 0.0,
                'hit_rate_at_k': 0.0,
                'k': k,
                'num_queries': 0
            }
        
        # Calculate metrics for each query
        precisions = []
        recalls = []
        f1s = []
        ndcgs = []
        
        for recommended, relevant in zip(all_recommended, all_relevant):
            precisions.append(cls.precision_at_k(recommended, relevant, k))
            recalls.append(cls.recall_at_k(recommended, relevant, k))
            f1s.append(cls.f1_at_k(recommended, relevant, k))
            ndcgs.append(cls.ndcg_at_k_binary(recommended, relevant, k))
        
        return {
            'precision_at_k': round(np.mean(precisions), 4),
            'recall_at_k': round(np.mean(recalls), 4),
            'f1_at_k': round(np.mean(f1s), 4),
            'ndcg_at_k': round(np.mean(ndcgs), 4),
            'map_at_k': round(cls.map_at_k(all_recommended, all_relevant, k), 4),
            'mrr': round(cls.mrr(all_recommended, all_relevant), 4),
            'hit_rate_at_k': round(cls.hit_rate_at_k(all_recommended, all_relevant, k), 4),
            'k': k,
            'num_queries': n
        }
