import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split

np.random.seed(42)

num_pairs = 2414

# Danh sách job và skills thực tế
job_titles = [
    "Data Scientist", "Machine Learning Engineer", "Software Engineer", "Data Analyst",
    "Business Analyst", "Product Manager", "Project Manager", "DevOps Engineer",
    "Cloud Architect", "Security Engineer", "QA Engineer", "Frontend Developer",
    "Backend Developer", "Fullstack Developer", "Mobile Developer", "UI/UX Designer",
    "Database Administrator", "System Administrator", "Network Engineer", "Data Engineer"
]

skills_db = {
    "Data Scientist": ["Python", "SQL", "Machine Learning", "Statistics", "TensorFlow", "PyTorch", "R", "Data Visualization"],
    "Software Engineer": ["Java", "Python", "Git", "Agile", "Data Structures", "Algorithms", "System Design"],
    "Data Analyst": ["SQL", "Excel", "Tableau", "Python", "Statistics", "Data Visualization", "Power BI"],
    "DevOps Engineer": ["Docker", "Kubernetes", "AWS", "CI/CD", "Linux", "Terraform", "Jenkins", "Git"],
    "Frontend Developer": ["JavaScript", "React", "HTML5", "CSS3", "TypeScript", "Vue.js", "Angular"],
    "Backend Developer": ["Python", "Java", "Node.js", "SQL", "REST APIs", "Microservices", "Django", "Spring Boot"],
    "ML Engineer": ["Python", "TensorFlow", "PyTorch", "MLOps", "Docker", "Kubernetes", "SQL", "AWS"],
    "Product Manager": ["Agile", "Scrum", "Product Strategy", "User Research", "Analytics", "Roadmapping", "JIRA"],
}

def generate_cv(job, level="Senior"):
    skills = skills_db.get(job, skills_db["Software Engineer"])
    selected_skills = np.random.choice(skills, size=np.random.randint(3, 6), replace=False)
    years = np.random.randint(2, 10)
    return f"{level} {job} with {years}+ years of experience. Proficient in {', '.join(selected_skills)}. Strong problem-solving and communication skills."

def generate_jd(job, level="Senior"):
    skills = skills_db.get(job, skills_db["Software Engineer"])
    selected_skills = np.random.choice(skills, size=np.random.randint(3, 6), replace=False)
    years = np.random.randint(2, 8)
    return f"We are hiring {level} {job}. Requirements: {years}+ years experience in {', '.join(selected_skills)}. Bachelor's degree required."

# Tạo dữ liệu
data = []
for i in range(1, num_pairs + 1):
    # Chọn job ngẫu nhiên
    job = np.random.choice(job_titles)
    level = np.random.choice(["Junior", "Mid-level", "Senior"])
    
    # Tạo CV và JD gốc
    cv_text = generate_cv(job, level)
    jd_text = generate_jd(job, level)
    
    # Quyết định label (70% match, 30% non-match)
    if np.random.random() < 0.3:  # Non-match
        # Chọn job khác hoàn toàn
        wrong_job = np.random.choice([j for j in job_titles if j != job])
        jd_text = generate_jd(wrong_job, level)
        label = 0
    else:
        label = 1
    
    data.append({
        "id": i,
        "cv_id": f"CV_{i:04d}",
        "jd_id": f"JD_{np.random.randint(1, 500):03d}",
        "cv_text": cv_text,
        "jd_text": jd_text,
        "label": label,
        "job_category": job
    })

df = pd.DataFrame(data)

# Chia train/test (80-20)
train_df, test_df = train_test_split(df, test_size=0.2, random_state=42, stratify=df['label'])

# Lưu file
train_df.to_csv("train_cv_jd_pairs.csv", index=False)
test_df.to_csv("test_cv_jd_pairs.csv", index=False)

print(f"✅ Train set: {len(train_df)} samples (Match: {sum(train_df['label']==1)}, Non-match: {sum(train_df['label']==0)})")
print(f"✅ Test set: {len(test_df)} samples (Match: {sum(test_df['label']==1)}, Non-match: {sum(test_df['label']==0)})")