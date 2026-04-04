"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { api, Application } from "@/lib/api";
import {
  Clock,
  MapPin,
  Building,
  Check,
  X,
  Eye,
  ChevronRight,
  AlertCircle,
} from "lucide-react";

export default function ApplicationsPage() {
  const [applications, setApplications] = useState<Application[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [filter, setFilter] = useState<string>("all");

  useEffect(() => {
    loadApplications();
  }, []);

  async function loadApplications() {
    try {
      // SỬA: dùng list() thay vì getMyApplications()
      const response = await api.applications.list();
      // SỬA: response là array trực tiếp, không có .data
      setApplications(Array.isArray(response) ? response : []);
    } catch (error) {
      console.error("Failed to load applications:", error);
      setApplications([]);
    } finally {
      setIsLoading(false);
    }
  }

  const filteredApplications = applications.filter((app) => {
    if (filter === "all") return true;
    return app.status === filter;
  });

  // FIX: Hàm validate và format match_score
  const getValidMatchScore = (score: number | undefined): number => {
    if (!score || isNaN(score)) return 0;
    // Nếu score > 1, coi như nó là percentage (0-100), clamp về 100
    if (score > 1) {
      return Math.min(Math.max(Math.round(score), 0), 100);
    }
    // Nếu score <= 1, coi như decimal (0-1), convert sang percentage
    return Math.min(Math.max(Math.round(score * 100), 0), 100);
  };

  // FIX: Hàm xác định màu sắc cho match score
  const getMatchScoreColor = (score: number): string => {
    if (score >= 80) return "text-emerald-500";
    if (score >= 60) return "text-amber-500";
    return "text-red-500";
  };

  function getStatusInfo(status: string) {
    switch (status) {
      case "shortlisted":
      case "hired":
        return {
          icon: Check,
          color: "bg-emerald-500/10 text-emerald-600 border-emerald-200",
          label: status === "hired" ? "Hired" : "Shortlisted",
          description:
            status === "hired"
              ? "Congratulations! You have been hired for this position."
              : "Congratulations! Your application has been shortlisted.",
        };
      case "rejected":
        return {
          icon: X,
          color: "bg-red-500/10 text-red-600 border-red-200",
          label: "Not Selected",
          description:
            "Unfortunately, you were not selected for this position.",
        };
      case "reviewed":
        return {
          icon: Eye,
          color: "bg-amber-500/10 text-amber-600 border-amber-200",
          label: "Reviewed",
          description: "The recruiter has reviewed your application.",
        };
      default:
        return {
          icon: Clock,
          color: "bg-blue-500/10 text-blue-600 border-blue-200",
          label: "Pending",
          description: "Your application is awaiting review.",
        };
    }
  }

  const statusCounts = {
    all: applications.length,
    pending: applications.filter((a) => a.status === "pending").length,
    reviewed: applications.filter((a) => a.status === "reviewed").length,
    shortlisted: applications.filter((a) => a.status === "shortlisted").length,
    hired: applications.filter((a) => a.status === "hired").length,
    rejected: applications.filter((a) => a.status === "rejected").length,
  };

  if (isLoading) {
    return (
      <div className="space-y-4">
        {[...Array(3)].map((_, i) => (
          <div
            key={i}
            className="bg-card rounded-xl border border-border p-6 animate-pulse"
          >
            <div className="h-6 w-48 bg-muted rounded mb-3"></div>
            <div className="h-4 w-32 bg-muted rounded mb-4"></div>
            <div className="h-20 w-full bg-muted rounded"></div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">My Applications</h1>
        <p className="text-muted-foreground mt-1">
          Track the status of your job applications
        </p>
      </div>

      {/* Status Tabs */}
      <div className="flex flex-wrap gap-2">
        {[
          { value: "all", label: "All", count: statusCounts.all },
          { value: "pending", label: "Pending", count: statusCounts.pending },
          {
            value: "reviewed",
            label: "Reviewed",
            count: statusCounts.reviewed,
          },
          {
            value: "shortlisted",
            label: "Shortlisted",
            count: statusCounts.shortlisted,
          },
          { value: "hired", label: "Hired", count: statusCounts.hired },
          {
            value: "rejected",
            label: "Not Selected",
            count: statusCounts.rejected,
          },
        ].map((tab) => (
          <button
            key={tab.value}
            onClick={() => setFilter(tab.value)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              filter === tab.value
                ? "bg-primary text-primary-foreground"
                : "bg-card border border-border hover:bg-muted"
            }`}
          >
            {tab.label} <span className="ml-1 opacity-70">({tab.count})</span>
          </button>
        ))}
      </div>

      {/* Applications List */}
      {filteredApplications.length === 0 ? (
        <div className="bg-card rounded-xl border border-border p-12 text-center">
          <div className="w-16 h-16 bg-muted rounded-full flex items-center justify-center mx-auto mb-4">
            <AlertCircle className="w-8 h-8 text-muted-foreground" />
          </div>
          <h3 className="text-lg font-medium mb-2">No applications found</h3>
          <p className="text-muted-foreground mb-6">
            {filter !== "all"
              ? "No applications with this status"
              : "You haven't applied to any jobs yet"}
          </p>
          {filter === "all" && (
            <Link
              href="/candidate/jobs"
              className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium"
            >
              Browse Jobs
              <ChevronRight className="w-4 h-4" />
            </Link>
          )}
        </div>
      ) : (
        <div className="space-y-4">
          {filteredApplications.map((app) => {
            const statusInfo = getStatusInfo(app.status);
            const StatusIcon = statusInfo.icon;
            // FIX: Validate match_score
            const validScore = getValidMatchScore(app.match_score);
            const scoreColor = getMatchScoreColor(validScore);
            // Tính toán stroke dasharray dựa trên percentage (0-100)
            const strokeDasharray = (validScore / 100) * 176;

            return (
              <div
                key={app.id}
                className="bg-card rounded-xl border border-border p-6 hover:shadow-lg transition-shadow"
              >
                <div className="flex flex-col md:flex-row md:items-start gap-4">
                  {/* Job Info */}
                  <div className="flex-1">
                    <div className="flex items-start justify-between mb-2">
                      <h3 className="text-lg font-semibold">
                        {app.job?.title || "Job Title"}
                      </h3>
                      <span
                        className={`px-3 py-1 rounded-full text-xs font-medium border ${statusInfo.color}`}
                      >
                        <StatusIcon className="w-3 h-3 inline mr-1" />
                        {statusInfo.label}
                      </span>
                    </div>
                    <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground mb-3">
                      {app.job?.company && (
                        <span className="flex items-center gap-1">
                          <Building className="w-4 h-4" />
                          {app.job.company}
                        </span>
                      )}
                      {app.job?.location && (
                        <span className="flex items-center gap-1">
                          <MapPin className="w-4 h-4" />
                          {app.job.location}
                        </span>
                      )}
                      <span className="flex items-center gap-1">
                        <Clock className="w-4 h-4" />
                        Applied {new Date(app.created_at).toLocaleDateString()}
                      </span>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {statusInfo.description}
                    </p>
                  </div>

                  {/* Match Score - FIXED */}
                  {app.match_score !== undefined && (
                    <div className="flex items-center gap-4 p-4 bg-muted/50 rounded-lg">
                      <div className="w-16 h-16 relative">
                        <svg className="w-16 h-16 -rotate-90">
                          <circle
                            cx="32"
                            cy="32"
                            r="28"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="4"
                            className="text-muted"
                          />
                          <circle
                            cx="32"
                            cy="32"
                            r="28"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="4"
                            strokeDasharray={`${strokeDasharray} 176`}
                            strokeLinecap="round"
                            className={scoreColor}
                          />
                        </svg>
                        <div className="absolute inset-0 flex items-center justify-center">
                          <span className="text-sm font-bold">
                            {validScore}%
                          </span>
                        </div>
                      </div>
                      <div>
                        <p className="text-sm font-medium">Match Score</p>
                        <p className="text-xs text-muted-foreground">
                          Based on your resume
                        </p>
                      </div>
                    </div>
                  )}
                </div>

                {/* Skills Summary */}
                {(app.matched_skills?.length || app.missing_skills?.length) && (
                  <div className="mt-4 pt-4 border-t border-border">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {app.matched_skills && app.matched_skills.length > 0 && (
                        <div>
                          <p className="text-sm font-medium mb-2 flex items-center gap-1">
                            <Check className="w-4 h-4 text-emerald-600" />
                            Matched Skills ({app.matched_skills.length})
                          </p>
                          <div className="flex flex-wrap gap-1">
                            {app.matched_skills.slice(0, 5).map((skill) => (
                              <span
                                key={skill}
                                className="px-2 py-0.5 bg-emerald-500/10 text-emerald-600 rounded text-xs"
                              >
                                {skill}
                              </span>
                            ))}
                            {app.matched_skills.length > 5 && (
                              <span className="text-xs text-muted-foreground">
                                +{app.matched_skills.length - 5} more
                              </span>
                            )}
                          </div>
                        </div>
                      )}
                      {app.missing_skills && app.missing_skills.length > 0 && (
                        <div>
                          <p className="text-sm font-medium mb-2 flex items-center gap-1">
                            <X className="w-4 h-4 text-amber-600" />
                            Skills to Develop ({app.missing_skills.length})
                          </p>
                          <div className="flex flex-wrap gap-1">
                            {app.missing_skills.slice(0, 5).map((skill) => (
                              <span
                                key={skill}
                                className="px-2 py-0.5 bg-amber-500/10 text-amber-600 rounded text-xs"
                              >
                                {skill}
                              </span>
                            ))}
                            {app.missing_skills.length > 5 && (
                              <span className="text-xs text-muted-foreground">
                                +{app.missing_skills.length - 5} more
                              </span>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
