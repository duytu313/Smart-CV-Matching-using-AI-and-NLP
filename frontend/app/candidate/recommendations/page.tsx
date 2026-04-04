"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { api, JobMatch } from "@/lib/api";
import {
  Sparkles,
  MapPin,
  Building,
  DollarSign,
  Clock,
  Check,
  X,
  ArrowRight,
  RefreshCw,
  Target,
  Zap,
  AlertCircle,
} from "lucide-react";

export default function RecommendationsPage() {
  const [recommendations, setRecommendations] = useState<JobMatch[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<"score" | "date">("score");

  useEffect(() => {
    loadRecommendations();
  }, []);

  async function loadRecommendations() {
    try {
      setIsLoading(true);
      setError(null);

      // Lấy resume chính của candidate
      const resumes = await api.resumes.list();
      const primaryResume = resumes.find((r) => r.is_primary);

      if (!primaryResume) {
        setRecommendations([]);
        return;
      }

      // Gọi API recommendations với resume_id
      const response = await api.recommendations.getRecommendations({
        resume_id: primaryResume.id,
        k: 20,
        min_score: 0.5,
      });

      // Validate và fix match_score (đảm bảo trong khoảng 0-100)
      const validatedRecommendations = (response.recommendations || []).map(
        (rec) => ({
          ...rec,
          match_score: Math.min(Math.max(rec.match_score, 0), 100),
        }),
      );

      setRecommendations(validatedRecommendations);
    } catch (error) {
      console.error("Failed to load recommendations:", error);
      setError(
        error instanceof Error
          ? error.message
          : "Failed to load recommendations",
      );
    } finally {
      setIsLoading(false);
    }
  }

  async function refreshRecommendations() {
    setIsRefreshing(true);
    setError(null);
    try {
      const resumes = await api.resumes.list();
      const primaryResume = resumes.find((r) => r.is_primary);

      if (!primaryResume) {
        setRecommendations([]);
        return;
      }

      const response = await api.recommendations.getRecommendations({
        resume_id: primaryResume.id,
        k: 20,
        min_score: 0.5,
      });

      // Validate và fix match_score
      const validatedRecommendations = (response.recommendations || []).map(
        (rec) => ({
          ...rec,
          match_score: Math.min(Math.max(rec.match_score, 0), 100),
        }),
      );

      setRecommendations(validatedRecommendations);
    } catch (error) {
      console.error("Failed to refresh recommendations:", error);
      setError(
        error instanceof Error
          ? error.message
          : "Failed to refresh recommendations",
      );
    } finally {
      setIsRefreshing(false);
    }
  }

  const sortedRecommendations = [...recommendations].sort((a, b) => {
    if (sortBy === "score") {
      return b.match_score - a.match_score;
    }
    return 0; // JobMatch doesn't have created_at, keep original order
  });

  // FIX: Hàm getScoreGrade nhận score từ 0-100
  function getScoreGrade(score: number): { label: string; color: string } {
    if (score >= 90)
      return { label: "Excellent Match", color: "text-emerald-600" };
    if (score >= 80) return { label: "Great Match", color: "text-emerald-500" };
    if (score >= 70) return { label: "Good Match", color: "text-blue-600" };
    if (score >= 60) return { label: "Fair Match", color: "text-amber-600" };
    return { label: "Partial Match", color: "text-muted-foreground" };
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
    return "";
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="space-y-4">
          {[...Array(5)].map((_, i) => (
            <div
              key={i}
              className="bg-card rounded-xl border border-border p-6 animate-pulse"
            >
              <div className="flex items-start gap-4">
                <div className="w-16 h-16 bg-muted rounded-lg"></div>
                <div className="flex-1">
                  <div className="h-6 w-48 bg-muted rounded mb-2"></div>
                  <div className="h-4 w-32 bg-muted rounded mb-4"></div>
                  <div className="h-20 w-full bg-muted rounded"></div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
          <AlertCircle className="w-12 h-12 text-red-600 mx-auto mb-3" />
          <p className="text-red-600 mb-2">Error loading recommendations</p>
          <p className="text-sm text-red-500 mb-4">{error}</p>
          <button
            onClick={loadRecommendations}
            className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Sparkles className="w-6 h-6 text-primary" />
            AI Job Recommendations
          </h1>
          <p className="text-muted-foreground mt-1">
            Personalized job matches based on your resume and skills
          </p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as "score" | "date")}
            className="px-3 py-2 border border-border rounded-lg bg-background text-sm"
          >
            <option value="score">Best Match</option>
            <option value="date">Most Recent</option>
          </select>
          <button
            onClick={refreshRecommendations}
            disabled={isRefreshing}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            <RefreshCw
              className={`w-4 h-4 ${isRefreshing ? "animate-spin" : ""}`}
            />
            Refresh
          </button>
        </div>
      </div>

      {/* Stats Banner */}
      {recommendations.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="bg-gradient-to-br from-primary/10 to-primary/5 rounded-xl p-4 border border-primary/20">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-primary/20 rounded-lg flex items-center justify-center">
                <Target className="w-5 h-5 text-primary" />
              </div>
              <div>
                <p className="text-2xl font-bold">{recommendations.length}</p>
                <p className="text-sm text-muted-foreground">Total Matches</p>
              </div>
            </div>
          </div>
          <div className="bg-gradient-to-br from-emerald-500/10 to-emerald-500/5 rounded-xl p-4 border border-emerald-500/20">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-emerald-500/20 rounded-lg flex items-center justify-center">
                <Zap className="w-5 h-5 text-emerald-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">
                  {recommendations.filter((r) => r.match_score >= 80).length}
                </p>
                <p className="text-sm text-muted-foreground">
                  Great Matches (80%+)
                </p>
              </div>
            </div>
          </div>
          <div className="bg-gradient-to-br from-blue-500/10 to-blue-500/5 rounded-xl p-4 border border-blue-500/20">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-blue-500/20 rounded-lg flex items-center justify-center">
                <Check className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">
                  {Math.round(
                    recommendations.reduce((sum, r) => sum + r.match_score, 0) /
                      recommendations.length,
                  )}
                  %
                </p>
                <p className="text-sm text-muted-foreground">Average Match</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Recommendations List */}
      {sortedRecommendations.length === 0 ? (
        <div className="bg-card rounded-xl border border-border p-12 text-center">
          <div className="w-20 h-20 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-4">
            <Sparkles className="w-10 h-10 text-primary" />
          </div>
          <h3 className="text-xl font-semibold mb-2">No Recommendations Yet</h3>
          <p className="text-muted-foreground mb-6 max-w-md mx-auto">
            Upload your resume to get personalized job recommendations based on
            your skills and experience.
          </p>
          <Link
            href="/candidate/resume"
            className="inline-flex items-center gap-2 px-6 py-3 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 transition-colors"
          >
            Upload Resume
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      ) : (
        <div className="space-y-4">
          {sortedRecommendations.map((rec, index) => {
            // FIX: Đảm bảo score là số nguyên từ 0-100
            const safeScore = Math.min(
              Math.max(Math.round(rec.match_score), 0),
              100,
            );
            const scoreGrade = getScoreGrade(safeScore);
            const scorePercent = safeScore;

            return (
              <div
                key={rec.job_id}
                className="bg-card rounded-xl border border-border overflow-hidden hover:shadow-lg transition-all"
              >
                <div className="p-6">
                  <div className="flex flex-col lg:flex-row lg:items-start gap-6">
                    {/* Rank Badge */}
                    <div className="flex lg:flex-col items-center gap-2 lg:gap-1">
                      <div
                        className={`w-10 h-10 rounded-lg flex items-center justify-center text-lg font-bold ${
                          index === 0
                            ? "bg-amber-500 text-white"
                            : index === 1
                              ? "bg-gray-400 text-white"
                              : index === 2
                                ? "bg-amber-700 text-white"
                                : "bg-muted text-muted-foreground"
                        }`}
                      >
                        #{index + 1}
                      </div>
                      <span className="text-xs text-muted-foreground">
                        Rank
                      </span>
                    </div>

                    {/* Job Info */}
                    <div className="flex-1">
                      <div className="flex items-start justify-between mb-3 flex-wrap gap-4">
                        <div>
                          <h3 className="text-xl font-semibold">{rec.title}</h3>
                          <div className="flex flex-wrap items-center gap-4 mt-2 text-sm text-muted-foreground">
                            {rec.company && (
                              <span className="flex items-center gap-1">
                                <Building className="w-4 h-4" />
                                {rec.company}
                              </span>
                            )}
                            {rec.location && (
                              <span className="flex items-center gap-1">
                                <MapPin className="w-4 h-4" />
                                {rec.location}
                              </span>
                            )}
                            {(rec.salary_min || rec.salary_max) && (
                              <span className="flex items-center gap-1">
                                <DollarSign className="w-4 h-4" />
                                {formatSalary(rec.salary_min, rec.salary_max)}
                              </span>
                            )}
                            {rec.job_type && (
                              <span className="flex items-center gap-1">
                                <Clock className="w-4 h-4" />
                                {rec.job_type}
                              </span>
                            )}
                          </div>
                        </div>

                        {/* Score Circle - FIXED: Sử dụng safeScore đã được clamp */}
                        <div className="flex flex-col items-center">
                          <div className="relative w-20 h-20">
                            <svg className="w-20 h-20 -rotate-90">
                              <circle
                                cx="40"
                                cy="40"
                                r="35"
                                fill="none"
                                stroke="currentColor"
                                strokeWidth="6"
                                className="text-muted"
                              />
                              <circle
                                cx="40"
                                cy="40"
                                r="35"
                                fill="none"
                                stroke="currentColor"
                                strokeWidth="6"
                                strokeDasharray={`${(safeScore / 100) * 220} 220`}
                                strokeLinecap="round"
                                className={
                                  scorePercent >= 80
                                    ? "text-emerald-500"
                                    : scorePercent >= 60
                                      ? "text-amber-500"
                                      : "text-red-500"
                                }
                              />
                            </svg>
                            <div className="absolute inset-0 flex items-center justify-center">
                              <span className="text-lg font-bold">
                                {scorePercent}%
                              </span>
                            </div>
                          </div>
                          <span
                            className={`text-xs font-medium mt-1 ${scoreGrade.color}`}
                          >
                            {scoreGrade.label}
                          </span>
                        </div>
                      </div>

                      {/* Skills */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                        {rec.matched_skills &&
                          rec.matched_skills.length > 0 && (
                            <div>
                              <p className="text-sm font-medium mb-2 flex items-center gap-1">
                                <Check className="w-4 h-4 text-emerald-600" />
                                Your Matching Skills (
                                {rec.matched_skills.length})
                              </p>
                              <div className="flex flex-wrap gap-1">
                                {rec.matched_skills.slice(0, 6).map((skill) => (
                                  <span
                                    key={skill}
                                    className="px-2 py-0.5 bg-emerald-500/10 text-emerald-600 rounded text-xs"
                                  >
                                    {skill}
                                  </span>
                                ))}
                                {rec.matched_skills.length > 6 && (
                                  <span className="text-xs text-muted-foreground">
                                    +{rec.matched_skills.length - 6} more
                                  </span>
                                )}
                              </div>
                            </div>
                          )}
                        {rec.missing_skills &&
                          rec.missing_skills.length > 0 && (
                            <div>
                              <p className="text-sm font-medium mb-2 flex items-center gap-1">
                                <X className="w-4 h-4 text-amber-600" />
                                Skills to Develop ({rec.missing_skills.length})
                              </p>
                              <div className="flex flex-wrap gap-1">
                                {rec.missing_skills.slice(0, 6).map((skill) => (
                                  <span
                                    key={skill}
                                    className="px-2 py-0.5 bg-amber-500/10 text-amber-600 rounded text-xs"
                                  >
                                    {skill}
                                  </span>
                                ))}
                                {rec.missing_skills.length > 6 && (
                                  <span className="text-xs text-muted-foreground">
                                    +{rec.missing_skills.length - 6} more
                                  </span>
                                )}
                              </div>
                            </div>
                          )}
                      </div>

                      {/* Explanation */}
                      {rec.recommendation_reason && (
                        <div className="mt-4 p-3 bg-primary/5 rounded-lg border border-primary/10">
                          <p className="text-sm text-muted-foreground flex items-start gap-2">
                            <Sparkles className="w-4 h-4 text-primary mt-0.5 flex-shrink-0" />
                            {rec.recommendation_reason}
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Actions */}
                <div className="px-6 py-4 bg-muted/30 border-t border-border flex items-center justify-end gap-3">
                  <Link
                    href={`/candidate/jobs/${rec.job_id}`}
                    className="text-sm font-medium text-primary hover:underline"
                  >
                    View Details
                  </Link>
                  <Link
                    href={`/candidate/jobs/${rec.job_id}/apply`}
                    className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors"
                  >
                    Apply Now
                  </Link>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
