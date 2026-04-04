"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api, Job } from "@/lib/api";
import {
  ArrowLeft,
  Building,
  MapPin,
  DollarSign,
  Briefcase,
  AlertCircle,
  Loader2,
  Send,
  FileText,
  Sparkles,
  Check,
  X,
} from "lucide-react";

export default function CandidateJobDetailPage() {
  const params = useParams();
  const router = useRouter();
  const jobId = params.id as string;

  const [job, setJob] = useState<Job | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isApplying, setIsApplying] = useState(false);
  const [showApplyModal, setShowApplyModal] = useState(false);
  const [coverLetter, setCoverLetter] = useState("");
  const [resumes, setResumes] = useState<any[]>([]);
  const [selectedResumeId, setSelectedResumeId] = useState<
    number | undefined
  >();
  const [applicationStatus, setApplicationStatus] = useState<string | null>(
    null,
  );
  const [matchScore, setMatchScore] = useState<any>(null);

  useEffect(() => {
    if (jobId) {
      loadJobDetails();
      loadResumes();
      checkApplicationStatus();
    }
  }, [jobId]);

  async function loadJobDetails() {
    try {
      setIsLoading(true);
      setError(null);
      const jobData = await api.jobs.get(parseInt(jobId));
      setJob(jobData);

      const userResumes = await api.resumes.list();
      const primaryResume = userResumes.find((r) => r.is_primary);
      if (primaryResume) {
        try {
          const matchData = await api.recommendations.getMatchExplanation(
            parseInt(jobId),
            primaryResume.id,
          );
          console.log("Match score data:", matchData);
          setMatchScore(matchData);
        } catch (err) {
          console.log("Match score not available");
        }
      }
    } catch (err) {
      console.error("Failed to load job:", err);
      setError(
        err instanceof Error ? err.message : "Failed to load job details",
      );
    } finally {
      setIsLoading(false);
    }
  }

  async function loadResumes() {
    try {
      const userResumes = await api.resumes.list();
      setResumes(userResumes);
      const primaryResume = userResumes.find((r) => r.is_primary);
      if (primaryResume) {
        setSelectedResumeId(primaryResume.id);
      }
    } catch (err) {
      console.error("Failed to load resumes:", err);
    }
  }

  async function checkApplicationStatus() {
    try {
      const applications = await api.applications.getMyApplications();
      const existingApp = applications.find(
        (app) => app.job_id === parseInt(jobId),
      );
      if (existingApp) {
        setApplicationStatus(existingApp.status);
      }
    } catch (err) {
      console.error("Failed to check application status:", err);
    }
  }

  async function handleApply() {
    if (!selectedResumeId) {
      alert("Please select a resume to apply with");
      return;
    }

    setIsApplying(true);
    try {
      await api.applications.apply(
        parseInt(jobId),
        selectedResumeId,
        coverLetter || undefined,
      );
      setShowApplyModal(false);
      setApplicationStatus("pending");
      alert("Application submitted successfully!");
    } catch (err) {
      console.error("Failed to apply:", err);
      alert(
        err instanceof Error ? err.message : "Failed to submit application",
      );
    } finally {
      setIsApplying(false);
    }
  }

  function formatSalary(salaryMin?: number, salaryMax?: number): string {
    if (salaryMin && salaryMax) {
      return `$${(salaryMin / 1000).toFixed(0)}k - $${(salaryMax / 1000).toFixed(0)}k`;
    }
    if (salaryMin) {
      return `From $${(salaryMin / 1000).toFixed(0)}k`;
    }
    if (salaryMax) {
      return `Up to $${(salaryMax / 1000).toFixed(0)}k`;
    }
    return "Not specified";
  }

  function getStatusBadge(status: string) {
    const statusConfig: Record<string, { label: string; className: string }> = {
      pending: {
        label: "Pending Review",
        className: "bg-amber-500/10 text-amber-600",
      },
      reviewed: {
        label: "Under Review",
        className: "bg-blue-500/10 text-blue-600",
      },
      shortlisted: {
        label: "Shortlisted",
        className: "bg-purple-500/10 text-purple-600",
      },
      rejected: {
        label: "Not Selected",
        className: "bg-red-500/10 text-red-600",
      },
      hired: {
        label: "Hired",
        className: "bg-emerald-500/10 text-emerald-600",
      },
    };
    const config = statusConfig[status] || {
      label: status,
      className: "bg-gray-500/10 text-gray-600",
    };
    return (
      <span
        className={`px-2 py-1 rounded-full text-xs font-medium ${config.className}`}
      >
        {config.label}
      </span>
    );
  }

  // Hàm tính phần trăm chính xác
  const formatPercentage = (value: number | undefined): string => {
    if (value === undefined || value === null) return "0";
    // Nếu value > 1, coi như đã là phần trăm (ví dụ: 65.6)
    if (value > 1) {
      return value.toFixed(1);
    }
    // Nếu value <= 1, nhân với 100 (ví dụ: 0.656 -> 65.6)
    return (value * 100).toFixed(1);
  };

  // Tính các giá trị phần trăm
  const overallScore = matchScore?.overall_score || 0;
  const overallMatchPercent = formatPercentage(overallScore);

  // Skills match - có thể từ skill_analysis hoặc tính từ matched_skills
  let skillsMatchPercent = "0";
  if (matchScore?.skill_analysis?.skill_match_percentage !== undefined) {
    skillsMatchPercent = formatPercentage(
      matchScore.skill_analysis.skill_match_percentage,
    );
  } else if (matchScore?.matched_skills_by_category) {
    // Tính toán từ matched_skills nếu có
    const allMatchedSkills = Object.values(
      matchScore.matched_skills_by_category || {},
    ).flat() as string[];
    const allSkills = job?.required_skills || [];
    if (allSkills.length > 0) {
      const percent = (allMatchedSkills.length / allSkills.length) * 100;
      skillsMatchPercent = percent.toFixed(1);
    }
  }

  const semanticValue = matchScore?.semantic_similarity || 0;
  const semanticMatchPercent = formatPercentage(semanticValue);

  // Đếm số lượng matched và total skills
  const totalMatchedSkills = matchScore?.matched_skills_by_category
    ? Object.values(matchScore.matched_skills_by_category).flat().length
    : 0;
  const totalRequiredSkills = job?.required_skills?.length || 0;

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background">
        <div className="max-w-4xl mx-auto px-4 py-8">
          <div className="animate-pulse space-y-6">
            <div className="h-8 w-32 bg-muted rounded"></div>
            <div className="bg-card rounded-xl border border-border p-6 space-y-4">
              <div className="h-8 w-3/4 bg-muted rounded"></div>
              <div className="h-4 w-1/2 bg-muted rounded"></div>
              <div className="h-32 w-full bg-muted rounded"></div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error || !job) {
    return (
      <div className="min-h-screen bg-background">
        <div className="max-w-4xl mx-auto px-4 py-8">
          <div className="bg-red-50 border border-red-200 rounded-lg p-8 text-center">
            <AlertCircle className="w-12 h-12 text-red-600 mx-auto mb-3" />
            <h2 className="text-xl font-semibold text-red-800 mb-2">
              Job Not Found
            </h2>
            <p className="text-red-600 mb-4">
              {error || "The job you're looking for doesn't exist."}
            </p>
            <Link
              href="/candidate/jobs"
              className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
            >
              <ArrowLeft className="w-4 h-4" />
              Back to Jobs
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Back Button */}
        <Link
          href="/candidate/jobs"
          className="inline-flex items-center gap-2 text-muted-foreground hover:text-foreground mb-6 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Jobs
        </Link>

        {/* Job Header */}
        <div className="bg-card rounded-xl border border-border p-6 mb-6">
          <div className="flex items-start justify-between flex-wrap gap-4">
            <div className="flex-1">
              <h1 className="text-2xl font-bold mb-2">{job.title}</h1>
              <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
                {job.company && (
                  <span className="flex items-center gap-1">
                    <Building className="w-4 h-4" />
                    {job.company}
                  </span>
                )}
                {job.location && (
                  <span className="flex items-center gap-1">
                    <MapPin className="w-4 h-4" />
                    {job.location}
                  </span>
                )}
                {job.job_type && (
                  <span className="flex items-center gap-1">
                    <Briefcase className="w-4 h-4" />
                    {job.job_type}
                  </span>
                )}
                {(job.salary_min || job.salary_max) && (
                  <span className="flex items-center gap-1">
                    <DollarSign className="w-4 h-4" />
                    {formatSalary(job.salary_min, job.salary_max)}
                  </span>
                )}
              </div>
            </div>
            {applicationStatus ? (
              <div className="text-right">
                <div className="mb-2">{getStatusBadge(applicationStatus)}</div>
                <p className="text-xs text-muted-foreground">
                  Application submitted
                </p>
              </div>
            ) : (
              <button
                onClick={() => setShowApplyModal(true)}
                className="px-6 py-2 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 transition-colors"
              >
                Apply Now
              </button>
            )}
          </div>
        </div>

        {/* Match Score Section */}
        {matchScore && (
          <div className="bg-gradient-to-r from-primary/10 to-primary/5 rounded-xl border border-primary/20 p-6 mb-6">
            <div className="flex items-center gap-3 mb-4">
              <Sparkles className="w-5 h-5 text-primary" />
              <h2 className="text-lg font-semibold">Your Match Score</h2>
            </div>
            <div className="flex items-center gap-6 flex-wrap">
              <div className="text-center">
                <div className="text-4xl font-bold text-primary">
                  {overallMatchPercent}%
                </div>
                <p className="text-sm text-muted-foreground">Overall Match</p>
              </div>
              <div className="flex-1">
                <div className="space-y-3">
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span>Skills Match</span>
                      <span className="font-medium">{skillsMatchPercent}%</span>
                    </div>
                    <div className="h-2 bg-muted rounded-full overflow-hidden">
                      <div
                        className="h-full bg-primary rounded-full transition-all duration-500"
                        style={{
                          width: `${Math.min(parseFloat(skillsMatchPercent), 100)}%`,
                        }}
                      />
                    </div>
                    {totalMatchedSkills > 0 && totalRequiredSkills > 0 && (
                      <p className="text-xs text-muted-foreground mt-1">
                        {totalMatchedSkills} of {totalRequiredSkills} required
                        skills matched
                      </p>
                    )}
                  </div>
                  {matchScore.semantic_similarity !== undefined && (
                    <div>
                      <div className="flex justify-between text-sm mb-1">
                        <span>Semantic Match</span>
                        <span className="font-medium">
                          {semanticMatchPercent}%
                        </span>
                      </div>
                      <div className="h-2 bg-muted rounded-full overflow-hidden">
                        <div
                          className="h-full bg-blue-500 rounded-full transition-all duration-500"
                          style={{
                            width: `${Math.min(parseFloat(semanticMatchPercent), 100)}%`,
                          }}
                        />
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Matched Skills by Category */}
            {matchScore.matched_skills_by_category &&
              Object.keys(matchScore.matched_skills_by_category).length > 0 && (
                <div className="mt-4 pt-4 border-t border-primary/20">
                  <p className="text-sm font-medium mb-2 flex items-center gap-2">
                    <Check className="w-4 h-4 text-emerald-600" />
                    Your Matching Skills:
                  </p>
                  <div className="space-y-3">
                    {Object.entries(matchScore.matched_skills_by_category).map(
                      ([category, skills]) => {
                        const skillsArray = skills as string[];
                        if (skillsArray.length === 0) return null;
                        return (
                          <div key={category}>
                            <p className="text-xs text-muted-foreground mb-1 capitalize">
                              {category.replace(/_/g, " ")}
                            </p>
                            <div className="flex flex-wrap gap-2">
                              {skillsArray.map((skill: string, idx: number) => (
                                <span
                                  key={idx}
                                  className="px-2 py-1 bg-emerald-500/10 text-emerald-600 rounded-md text-xs"
                                >
                                  {skill}
                                </span>
                              ))}
                            </div>
                          </div>
                        );
                      },
                    )}
                  </div>
                </div>
              )}

            {/* Missing Skills by Category */}
            {matchScore.missing_skills_by_category &&
              Object.keys(matchScore.missing_skills_by_category).length > 0 && (
                <div className="mt-4 pt-4 border-t border-primary/20">
                  <p className="text-sm font-medium mb-2 flex items-center gap-2">
                    <X className="w-4 h-4 text-amber-600" />
                    Skills to Develop:
                  </p>
                  <div className="space-y-3">
                    {Object.entries(matchScore.missing_skills_by_category).map(
                      ([category, skills]) => {
                        const skillsArray = skills as string[];
                        if (skillsArray.length === 0) return null;
                        return (
                          <div key={category}>
                            <p className="text-xs text-muted-foreground mb-1 capitalize">
                              {category.replace(/_/g, " ")}
                            </p>
                            <div className="flex flex-wrap gap-2">
                              {skillsArray.map((skill: string, idx: number) => (
                                <span
                                  key={idx}
                                  className="px-2 py-1 bg-amber-500/10 text-amber-600 rounded-md text-xs"
                                >
                                  {skill}
                                </span>
                              ))}
                            </div>
                          </div>
                        );
                      },
                    )}
                  </div>
                </div>
              )}

            {/* Skill Suggestions */}
            {matchScore.skill_suggestions &&
              matchScore.skill_suggestions.length > 0 && (
                <div className="mt-4 pt-4 border-t border-primary/20">
                  <p className="text-sm font-medium mb-2 flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-primary" />
                    Recommended Skills to Learn:
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {matchScore.skill_suggestions
                      .slice(0, 10)
                      .map((skill: string, idx: number) => (
                        <span
                          key={idx}
                          className="px-2 py-1 bg-primary/10 text-primary rounded-md text-xs"
                        >
                          {skill}
                        </span>
                      ))}
                  </div>
                </div>
              )}
          </div>
        )}

        {/* Job Description */}
        <div className="bg-card rounded-xl border border-border p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4">Job Description</h2>
          <div className="prose prose-sm max-w-none">
            <p className="text-muted-foreground whitespace-pre-wrap">
              {job.description}
            </p>
          </div>
        </div>

        {/* Requirements */}
        {job.requirements && (
          <div className="bg-card rounded-xl border border-border p-6 mb-6">
            <h2 className="text-lg font-semibold mb-4">Requirements</h2>
            <div className="prose prose-sm max-w-none">
              <p className="text-muted-foreground whitespace-pre-wrap">
                {job.requirements}
              </p>
            </div>
          </div>
        )}

        {/* Required Skills */}
        {job.required_skills && job.required_skills.length > 0 && (
          <div className="bg-card rounded-xl border border-border p-6">
            <h2 className="text-lg font-semibold mb-4">Required Skills</h2>
            <div className="flex flex-wrap gap-2">
              {job.required_skills.map((skill) => (
                <span
                  key={skill}
                  className="px-3 py-1 bg-muted rounded-full text-sm"
                >
                  {skill}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Apply Modal */}
      {showApplyModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-card rounded-xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-border">
              <h2 className="text-xl font-semibold">Apply for {job.title}</h2>
            </div>

            <div className="p-6 space-y-4">
              {/* Resume Selection */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Select Resume <span className="text-red-500">*</span>
                </label>
                {resumes.length === 0 ? (
                  <div className="text-center p-4 bg-muted/30 rounded-lg">
                    <FileText className="w-8 h-8 text-muted-foreground mx-auto mb-2" />
                    <p className="text-sm text-muted-foreground mb-2">
                      No resume uploaded
                    </p>
                    <Link
                      href="/candidate/resume"
                      className="text-sm text-primary hover:underline"
                    >
                      Upload a resume first
                    </Link>
                  </div>
                ) : (
                  <select
                    value={selectedResumeId}
                    onChange={(e) =>
                      setSelectedResumeId(parseInt(e.target.value))
                    }
                    className="w-full px-4 py-2 border border-border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
                  >
                    {resumes.map((resume) => (
                      <option key={resume.id} value={resume.id}>
                        {resume.title} {resume.is_primary ? "(Primary)" : ""}
                      </option>
                    ))}
                  </select>
                )}
              </div>

              {/* Cover Letter */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Cover Letter (Optional)
                </label>
                <textarea
                  value={coverLetter}
                  onChange={(e) => setCoverLetter(e.target.value)}
                  rows={6}
                  placeholder="Write a cover letter to the recruiter..."
                  className="w-full px-4 py-2 border border-border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/20 resize-none"
                />
              </div>
            </div>

            <div className="p-6 border-t border-border flex justify-end gap-3">
              <button
                onClick={() => setShowApplyModal(false)}
                className="px-4 py-2 border border-border rounded-lg font-medium hover:bg-muted transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleApply}
                disabled={isApplying || resumes.length === 0}
                className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 transition-colors disabled:opacity-50"
              >
                {isApplying ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Submitting...
                  </>
                ) : (
                  <>
                    <Send className="w-4 h-4" />
                    Submit Application
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
