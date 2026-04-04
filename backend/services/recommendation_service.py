"""
Job Recommendation Service.
Implements AI-based job matching using embeddings and FAISS for efficient similarity search.
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from .embedding_service import EmbeddingService
from .skill_service import SkillService


@dataclass
class JobMatch:
    """Represents a job match with score and analysis."""
    job_id: int
    title: str
    company: str
    match_score: float
    matched_skills: List[str]
    missing_skills: List[str]
    skill_match_percentage: float
    recommendation_reason: str


class VectorIndex:
    """
    In-memory vector index using FAISS for efficient similarity search.
    Falls back to numpy-based search if FAISS is unavailable.
    """
    
    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self.index = None
        self.id_map = {}  # Maps internal index to job_id
        self.embeddings = []  # Fallback storage
        self._use_faiss = False
        
        try:
            import faiss
            self.index = faiss.IndexFlatIP(dimension)  # Inner product (cosine sim with normalized vectors)
            self._use_faiss = True
        except ImportError:
            print("FAISS not available, using numpy fallback")
            self._use_faiss = False
    
    def add(self, job_id: int, embedding: np.ndarray):
        """Add a job embedding to the index."""
        if embedding is None:
            return
        
        # Normalize for cosine similarity
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        
        internal_id = len(self.id_map)
        self.id_map[internal_id] = job_id
        
        if self._use_faiss:
            self.index.add(embedding.reshape(1, -1).astype(np.float32))
        else:
            self.embeddings.append(embedding)
    
    def search(self, query_embedding: np.ndarray, k: int = 10) -> List[Tuple[int, float]]:
        """
        Search for top-k similar jobs.
        
        Args:
            query_embedding: Query embedding vector
            k: Number of results to return
            
        Returns:
            List of (job_id, similarity_score) tuples
        """
        if query_embedding is None:
            return []
        
        # Normalize query
        norm = np.linalg.norm(query_embedding)
        if norm > 0:
            query_embedding = query_embedding / norm
        
        if self._use_faiss and self.index.ntotal > 0:
            # FAISS search
            k = min(k, self.index.ntotal)
            scores, indices = self.index.search(
                query_embedding.reshape(1, -1).astype(np.float32), 
                k
            )
            results = []
            for idx, score in zip(indices[0], scores[0]):
                if idx >= 0 and idx in self.id_map:
                    results.append((self.id_map[idx], float(score)))
            return results
        elif self.embeddings:
            # Numpy fallback
            embeddings_matrix = np.vstack(self.embeddings)
            scores = np.dot(embeddings_matrix, query_embedding)
            top_indices = np.argsort(scores)[::-1][:k]
            return [(self.id_map[int(idx)], float(scores[idx])) for idx in top_indices]
        
        return []
    
    def clear(self):
        """Clear the index."""
        if self._use_faiss:
            import faiss
            self.index = faiss.IndexFlatIP(self.dimension)
        self.embeddings = []
        self.id_map = {}


class RecommendationService:
    """
    Main service for generating job recommendations.
    Combines embedding-based similarity with skill matching.
    """
    
    def __init__(self):
        self.vector_index = VectorIndex()
        self.job_cache = {}  # Cache job data for quick access
    
    def index_job(self, job_id: int, job_data: Dict):
        """
        Add a job to the recommendation index.
        
        Args:
            job_id: Unique job identifier
            job_data: Job data including description and skills
        """
        # Generate embedding from job description
        text = f"{job_data.get('title', '')} {job_data.get('description', '')} {job_data.get('requirements', '')}"
        embedding = EmbeddingService.generate_embedding(text)
        
        if embedding is not None:
            self.vector_index.add(job_id, embedding)
            self.job_cache[job_id] = job_data
    
    def index_jobs_batch(self, jobs: List[Dict]):
        """Index multiple jobs efficiently."""
        texts = []
        job_ids = []
        
        for job in jobs:
            job_id = job.get('id')
            if job_id:
                text = f"{job.get('title', '')} {job.get('description', '')} {job.get('requirements', '')}"
                texts.append(text)
                job_ids.append(job_id)
                self.job_cache[job_id] = job
        
        embeddings = EmbeddingService.generate_embeddings_batch(texts)
        
        for job_id, embedding in zip(job_ids, embeddings):
            if embedding is not None:
                self.vector_index.add(job_id, embedding)
    
    def recommend_jobs(
        self,
        resume_text: str,
        resume_skills: List[str],
        k: int = 10,
        min_score: float = 0.3
    ) -> List[JobMatch]:
        """
        Generate job recommendations for a resume.
        
        Args:
            resume_text: Full resume text
            resume_skills: Extracted skills from resume
            k: Number of recommendations to return
            min_score: Minimum match score threshold
            
        Returns:
            List of JobMatch objects sorted by score
        """
        # Generate resume embedding
        resume_embedding = EmbeddingService.generate_embedding(resume_text)
        
        if resume_embedding is None:
            return []
        
        # Get candidates from vector search
        candidates = self.vector_index.search(resume_embedding, k * 2)  # Get more for filtering
        
        matches = []
        for job_id, embedding_score in candidates:
            job_data = self.job_cache.get(job_id)
            if not job_data:
                continue
            
            # Calculate skill match
            job_required = job_data.get('required_skills', [])
            job_preferred = job_data.get('preferred_skills', [])
            
            skill_analysis = SkillService.calculate_skill_score(
                resume_skills,
                job_required,
                job_preferred
            )
            
            # Combine embedding score and skill score
            # Embedding score is 0-1, skill score is 0-100
            embedding_weight = 0.6
            skill_weight = 0.4
            
            combined_score = (
                embedding_score * embedding_weight * 100 +
                skill_analysis['total_score'] * skill_weight
            )
            
            if combined_score < min_score * 100:
                continue
            
            # Generate recommendation reason
            reason = self._generate_reason(
                skill_analysis,
                embedding_score,
                job_data.get('title', '')
            )
            
            matches.append(JobMatch(
                job_id=job_id,
                title=job_data.get('title', ''),
                company=job_data.get('company', ''),
                match_score=round(combined_score, 1),
                matched_skills=skill_analysis['all_matched'],
                missing_skills=skill_analysis['all_missing'],
                skill_match_percentage=skill_analysis['total_score'],
                recommendation_reason=reason
            ))
        
        # Sort by score and return top-k
        matches.sort(key=lambda x: x.match_score, reverse=True)
        return matches[:k]
    
    def _generate_reason(
        self,
        skill_analysis: Dict,
        embedding_score: float,
        job_title: str
    ) -> str:
        """Generate a human-readable recommendation reason."""
        reasons = []
        
        matched_count = len(skill_analysis['all_matched'])
        total_required = len(skill_analysis['required_skills']['matched']) + len(skill_analysis['required_skills']['missing'])
        
        if skill_analysis['total_score'] >= 80:
            reasons.append(f"Excellent skill match ({matched_count} matching skills)")
        elif skill_analysis['total_score'] >= 60:
            reasons.append(f"Strong skill match ({matched_count} matching skills)")
        elif skill_analysis['total_score'] >= 40:
            reasons.append(f"Good skill match ({matched_count} matching skills)")
        
        if embedding_score >= 0.8:
            reasons.append("Your experience closely aligns with this role")
        elif embedding_score >= 0.6:
            reasons.append("Your background is relevant to this position")
        
        if skill_analysis['required_skills']['missing']:
            missing_count = len(skill_analysis['required_skills']['missing'])
            if missing_count <= 2:
                reasons.append(f"Only {missing_count} required skill(s) to develop")
        
        if not reasons:
            reasons.append(f"Potential match for {job_title}")
        
        return ". ".join(reasons) + "."
    
    def get_match_explanation(
        self,
        resume_text: str,
        resume_skills: List[str],
        job_id: int
    ) -> Optional[Dict]:
        """
        Get detailed match explanation for a specific job.
        
        Args:
            resume_text: Full resume text
            resume_skills: Extracted skills from resume
            job_id: Job to explain match for
            
        Returns:
            Detailed match analysis dictionary
        """
        job_data = self.job_cache.get(job_id)
        if not job_data:
            return None
        
        # Calculate embedding similarity
        resume_embedding = EmbeddingService.generate_embedding(resume_text)
        job_text = f"{job_data.get('title', '')} {job_data.get('description', '')} {job_data.get('requirements', '')}"
        job_embedding = EmbeddingService.generate_embedding(job_text)
        
        embedding_score = EmbeddingService.cosine_similarity(resume_embedding, job_embedding)
        
        # Calculate skill match
        skill_analysis = SkillService.calculate_skill_score(
            resume_skills,
            job_data.get('required_skills', []),
            job_data.get('preferred_skills', [])
        )
        
        # Categorize matched and missing skills
        matched_categorized = SkillService.categorize_skills(skill_analysis['all_matched'])
        missing_categorized = SkillService.categorize_skills(skill_analysis['all_missing'])
        
        return {
            "job": {
                "id": job_id,
                "title": job_data.get('title'),
                "company": job_data.get('company')
            },
            "overall_score": round(
                embedding_score * 60 + skill_analysis['total_score'] * 0.4,
                1
            ),
            "semantic_similarity": round(embedding_score * 100, 1),
            "skill_analysis": skill_analysis,
            "matched_skills_by_category": matched_categorized,
            "missing_skills_by_category": missing_categorized,
            "skill_suggestions": SkillService.suggest_skills(resume_skills)
        }


# Global recommendation service instance
recommendation_service = RecommendationService()
