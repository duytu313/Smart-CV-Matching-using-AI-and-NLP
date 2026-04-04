"""
Skill Extraction and Matching Service.
Handles skill extraction from text and skill matching between resumes and jobs.
"""

import re
from typing import List, Set, Dict, Tuple, Optional
from collections import defaultdict


# Comprehensive skill database organized by category
SKILL_DATABASE = {
    "programming_languages": [
        "python", "javascript", "typescript", "java", "c++", "c#", "c",
        "ruby", "go", "golang", "rust", "swift", "kotlin", "scala", "r",
        "php", "perl", "matlab", "julia", "haskell", "elixir", "clojure",
        "objective-c", "dart", "lua", "groovy", "fortran", "cobol", "assembly"
    ],
    "web_frameworks": [
        "react", "reactjs", "react.js", "angular", "angularjs", "vue", "vuejs",
        "vue.js", "nextjs", "next.js", "nuxt", "nuxtjs", "svelte", "ember",
        "backbone", "jquery", "express", "expressjs", "fastapi", "django",
        "flask", "spring", "spring boot", "rails", "ruby on rails", "laravel",
        "asp.net", ".net", "dotnet", "node", "nodejs", "node.js", "nestjs"
    ],
    "databases": [
        "sql", "mysql", "postgresql", "postgres", "mongodb", "redis",
        "elasticsearch", "cassandra", "dynamodb", "sqlite", "oracle",
        "sql server", "mssql", "mariadb", "couchdb", "neo4j", "graphql",
        "firebase", "supabase", "prisma", "sequelize", "typeorm"
    ],
    "cloud_platforms": [
        "aws", "amazon web services", "azure", "microsoft azure", "gcp",
        "google cloud", "google cloud platform", "heroku", "digitalocean",
        "vercel", "netlify", "cloudflare", "linode", "vultr"
    ],
    "devops": [
        "docker", "kubernetes", "k8s", "jenkins", "gitlab ci", "github actions",
        "circleci", "travis ci", "terraform", "ansible", "puppet", "chef",
        "vagrant", "nginx", "apache", "linux", "unix", "bash", "shell",
        "powershell", "ci/cd", "cicd", "continuous integration", "continuous deployment"
    ],
    "data_science": [
        "machine learning", "ml", "deep learning", "dl", "artificial intelligence",
        "ai", "data science", "data analysis", "data analytics", "statistics",
        "tensorflow", "pytorch", "keras", "scikit-learn", "sklearn", "pandas",
        "numpy", "scipy", "matplotlib", "seaborn", "plotly", "tableau",
        "power bi", "jupyter", "nlp", "natural language processing",
        "computer vision", "neural networks", "regression", "classification"
    ],
    "mobile": [
        "ios", "android", "react native", "flutter", "xamarin", "ionic",
        "cordova", "phonegap", "swift", "kotlin", "objective-c", "mobile development"
    ],
    "tools": [
        "git", "github", "gitlab", "bitbucket", "jira", "confluence",
        "trello", "asana", "slack", "notion", "figma", "sketch", "adobe xd",
        "photoshop", "illustrator", "vs code", "visual studio", "intellij",
        "pycharm", "postman", "insomnia", "swagger"
    ],
    "soft_skills": [
        "leadership", "communication", "teamwork", "problem solving",
        "critical thinking", "time management", "project management",
        "agile", "scrum", "kanban", "collaboration", "mentoring",
        "presentation", "negotiation", "conflict resolution", "adaptability"
    ],
    "security": [
        "cybersecurity", "security", "penetration testing", "ethical hacking",
        "owasp", "encryption", "ssl", "tls", "oauth", "jwt", "authentication",
        "authorization", "sso", "ldap", "active directory"
    ],
    "testing": [
        "unit testing", "integration testing", "e2e testing", "end-to-end testing",
        "jest", "mocha", "chai", "pytest", "junit", "selenium", "cypress",
        "playwright", "puppeteer", "tdd", "bdd", "test driven development"
    ]
}

# Create a flat set of all skills for quick lookup
ALL_SKILLS = set()
SKILL_TO_CATEGORY = {}
SKILL_ALIASES = {}

for category, skills in SKILL_DATABASE.items():
    for skill in skills:
        ALL_SKILLS.add(skill.lower())
        SKILL_TO_CATEGORY[skill.lower()] = category

# Add common aliases
SKILL_ALIASES.update({
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
    "postgres": "postgresql",
    "mongo": "mongodb",
    "k8s": "kubernetes",
    "tf": "tensorflow",
    "scikit learn": "scikit-learn",
    "react js": "react",
    "vue js": "vue",
    "node js": "nodejs",
    "next js": "nextjs"
})


class SkillService:
    """
    Service for extracting and matching skills from text.
    Uses pattern matching and NLP techniques.
    """
    
    @classmethod
    def extract_skills(cls, text: str) -> List[str]:
        """
        Extract skills from text using pattern matching.
        
        Args:
            text: Input text (resume or job description)
            
        Returns:
            List of extracted skills (normalized)
        """
        if not text:
            return []
        
        text_lower = text.lower()
        found_skills = set()
        
        # First, try to find multi-word skills
        for skill in ALL_SKILLS:
            if len(skill.split()) > 1:  # Multi-word skill
                if skill in text_lower:
                    found_skills.add(skill)
        
        # Then find single-word skills with word boundaries
        words = set(re.findall(r'\b[\w\+\#\.]+\b', text_lower))
        
        for word in words:
            # Check if word is a skill
            if word in ALL_SKILLS:
                found_skills.add(word)
            # Check aliases
            elif word in SKILL_ALIASES:
                found_skills.add(SKILL_ALIASES[word])
        
        # Also check for skills in common patterns like "experience with X"
        patterns = [
            r'experience (?:with|in) ([\w\+\#\.]+)',
            r'proficient in ([\w\+\#\.]+)',
            r'knowledge of ([\w\+\#\.]+)',
            r'skilled in ([\w\+\#\.]+)',
            r'expertise in ([\w\+\#\.]+)',
            r'familiar with ([\w\+\#\.]+)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                if match in ALL_SKILLS:
                    found_skills.add(match)
                elif match in SKILL_ALIASES:
                    found_skills.add(SKILL_ALIASES[match])
        
        return sorted(list(found_skills))
    
    @classmethod
    def categorize_skills(cls, skills: List[str]) -> Dict[str, List[str]]:
        """
        Organize skills by category.
        
        Args:
            skills: List of skill names
            
        Returns:
            Dictionary mapping categories to skills
        """
        categorized = defaultdict(list)
        
        for skill in skills:
            skill_lower = skill.lower()
            category = SKILL_TO_CATEGORY.get(skill_lower, "other")
            categorized[category].append(skill)
        
        return dict(categorized)
    
    @classmethod
    def match_skills(
        cls, 
        resume_skills: List[str], 
        job_skills: List[str]
    ) -> Tuple[List[str], List[str], float]:
        """
        Match skills between resume and job requirements.
        
        Args:
            resume_skills: Skills from the resume
            job_skills: Required skills from the job
            
        Returns:
            Tuple of (matched_skills, missing_skills, match_percentage)
        """
        resume_set = set(s.lower() for s in resume_skills)
        job_set = set(s.lower() for s in job_skills)
        
        # Resolve aliases for better matching
        resolved_resume = set()
        for skill in resume_set:
            resolved_resume.add(SKILL_ALIASES.get(skill, skill))
        
        resolved_job = set()
        for skill in job_set:
            resolved_job.add(SKILL_ALIASES.get(skill, skill))
        
        matched = resolved_resume.intersection(resolved_job)
        missing = resolved_job - resolved_resume
        
        match_percentage = 0.0
        if resolved_job:
            match_percentage = len(matched) / len(resolved_job) * 100
        
        return (
            sorted(list(matched)),
            sorted(list(missing)),
            round(match_percentage, 1)
        )
    
    @classmethod
    def calculate_skill_score(
        cls,
        resume_skills: List[str],
        required_skills: List[str],
        preferred_skills: Optional[List[str]] = None
    ) -> Dict:
        """
        Calculate detailed skill match score.
        
        Args:
            resume_skills: Skills from the resume
            required_skills: Required skills for the job
            preferred_skills: Nice-to-have skills
            
        Returns:
            Dictionary with detailed scoring breakdown
        """
        # Match required skills (weighted higher)
        req_matched, req_missing, req_percentage = cls.match_skills(
            resume_skills, required_skills
        )
        
        # Match preferred skills
        pref_matched = []
        pref_missing = []
        pref_percentage = 0.0
        
        if preferred_skills:
            pref_matched, pref_missing, pref_percentage = cls.match_skills(
                resume_skills, preferred_skills
            )
        
        # Calculate weighted score (required skills worth 70%, preferred 30%)
        total_score = req_percentage * 0.7
        if preferred_skills:
            total_score += pref_percentage * 0.3
        else:
            total_score = req_percentage  # If no preferred, use only required
        
        return {
            "total_score": round(total_score, 1),
            "required_skills": {
                "matched": req_matched,
                "missing": req_missing,
                "percentage": req_percentage
            },
            "preferred_skills": {
                "matched": pref_matched,
                "missing": pref_missing,
                "percentage": pref_percentage
            },
            "all_matched": sorted(list(set(req_matched + pref_matched))),
            "all_missing": sorted(list(set(req_missing + pref_missing)))
        }
    
    @classmethod
    def suggest_skills(cls, current_skills: List[str], category: str = None) -> List[str]:
        """
        Suggest related skills based on current skills.
        
        Args:
            current_skills: User's current skills
            category: Optional category to focus on
            
        Returns:
            List of suggested skills
        """
        current_set = set(s.lower() for s in current_skills)
        suggestions = set()
        
        # Find categories of current skills
        user_categories = set()
        for skill in current_set:
            cat = SKILL_TO_CATEGORY.get(skill)
            if cat:
                user_categories.add(cat)
        
        # Suggest skills from the same categories
        for cat in user_categories:
            if category and cat != category:
                continue
            for skill in SKILL_DATABASE.get(cat, []):
                if skill.lower() not in current_set:
                    suggestions.add(skill)
        
        return sorted(list(suggestions))[:10]
