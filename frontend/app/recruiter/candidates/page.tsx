"use client";

import { useState, useEffect } from "react";
import { api, Application, Job, User } from "@/lib/api";
import {
  Search,
  Filter,
  ChevronDown,
  ChevronUp,
  Mail,
  FileText,
  Check,
  X,
  Clock,
  Star,
  RefreshCw,
  AlertCircle,
} from "lucide-react";

// Extended Application type với job và candidate đã được enrich
interface EnrichedApplication extends Application {
  job?: Job;
  candidate?: User;
}

export default function CandidatesPage() {
  const [applications, setApplications] = useState<EnrichedApplication[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [sortBy, setSortBy] = useState<"date" | "score">("score");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [updatingStatus, setUpdatingStatus] = useState<number | null>(null);

  useEffect(() => {
    loadApplications();
  }, []);

  // FIX: Hàm validate và format match_score
  function validateMatchScore(score: number | undefined): number {
    if (!score || isNaN(score)) return 0;
    // Nếu score > 1, coi như nó là percentage (0-100)
    if (score > 1) {
      return Math.min(Math.max(Math.round(score), 0), 100);
    }
    // Nếu score <= 1, coi như decimal (0-1), convert sang percentage
    return Math.min(Math.max(Math.round(score * 100), 0), 100);
  }

  async function loadApplications() {
    try {
      setIsLoading(true);
      setError(null);

      // Lấy tất cả applications
      const allApplications = await api.applications.list();
      console.log("All applications:", allApplications);

      // Lấy user hiện tại để biết recruiter_id
      const currentUser = await api.auth.me();
      console.log("Current user:", currentUser);

      // Lấy tất cả jobs của recruiter này
      const jobsResponse = await api.jobs.list({ page: 1, page_size: 100 });
      const allJobs = jobsResponse.jobs || [];
      const myJobs = allJobs.filter(
        (job) => job.recruiter_id === currentUser.id,
      );
      const myJobIds = new Set(myJobs.map((job) => job.id));

      // Lọc applications cho jobs của recruiter này và enrich data
      const myApplications: EnrichedApplication[] = allApplications
        .filter((app) => myJobIds.has(app.job_id))
        .map((app) => ({
          ...app,
          job: myJobs.find((job) => job.id === app.job_id),
          candidate: app.candidate || {
            id: 0,
            email: "",
            full_name: "Unknown Candidate",
            role: "candidate",
            created_at: new Date().toISOString(),
          },
        }));

      setApplications(myApplications);
    } catch (error) {
      console.error("Failed to load applications:", error);
      setError(
        error instanceof Error ? error.message : "Failed to load applications",
      );
    } finally {
      setIsLoading(false);
    }
  }

  async function updateApplicationStatus(appId: number, status: string) {
    try {
      setUpdatingStatus(appId);
      await api.applications.updateStatus(appId, status);
      setApplications(
        applications.map((app) =>
          app.id === appId ? { ...app, status: status as any } : app,
        ),
      );
    } catch (error) {
      console.error("Failed to update status:", error);
      setError(
        error instanceof Error ? error.message : "Failed to update status",
      );
    } finally {
      setUpdatingStatus(null);
    }
  }

  const filteredApplications = applications
    .filter((app) => {
      const matchesSearch =
        app.candidate?.full_name
          ?.toLowerCase()
          .includes(searchQuery.toLowerCase()) ||
        app.candidate?.email
          ?.toLowerCase()
          .includes(searchQuery.toLowerCase()) ||
        app.job?.title?.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesStatus =
        statusFilter === "all" || app.status === statusFilter;
      return matchesSearch && matchesStatus;
    })
    .sort((a, b) => {
      if (sortBy === "score") {
        const scoreA = validateMatchScore(a.match_score);
        const scoreB = validateMatchScore(b.match_score);
        return sortOrder === "desc" ? scoreB - scoreA : scoreA - scoreB;
      } else {
        const dateA = new Date(a.created_at).getTime();
        const dateB = new Date(b.created_at).getTime();
        return sortOrder === "desc" ? dateB - dateA : dateA - dateB;
      }
    });

  function getStatusColor(status: string) {
    switch (status) {
      case "hired":
        return "bg-emerald-500/10 text-emerald-600";
      case "rejected":
        return "bg-red-500/10 text-red-600";
      case "reviewed":
        return "bg-amber-500/10 text-amber-600";
      case "shortlisted":
        return "bg-purple-500/10 text-purple-600";
      case "pending":
        return "bg-blue-500/10 text-blue-600";
      default:
        return "bg-gray-500/10 text-gray-600";
    }
  }

  // FIX: Hàm xác định màu sắc cho match score (nhận percentage từ 0-100)
  function getScoreColor(scorePercentage: number) {
    if (scorePercentage >= 80) return "text-emerald-600";
    if (scorePercentage >= 60) return "text-amber-600";
    return "text-red-600";
  }

  function getStatusLabel(status: string) {
    const labels: Record<string, string> = {
      pending: "Pending",
      reviewed: "Reviewed",
      shortlisted: "Shortlisted",
      rejected: "Rejected",
      hired: "Hired",
    };
    return labels[status] || status;
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
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-muted rounded-full"></div>
                <div className="flex-1">
                  <div className="h-5 w-32 bg-muted rounded mb-2"></div>
                  <div className="h-4 w-48 bg-muted rounded"></div>
                </div>
                <div className="h-8 w-20 bg-muted rounded"></div>
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
          <p className="text-red-600 mb-2">Error loading applications</p>
          <p className="text-sm text-red-500 mb-4">{error}</p>
          <button
            onClick={loadApplications}
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
      <div>
        <h1 className="text-2xl font-bold">Candidates</h1>
        <p className="text-muted-foreground mt-1">
          Review and manage job applications
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search by candidate name, email, or job title..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-muted-foreground" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 border border-border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
          >
            <option value="all">All Status</option>
            <option value="pending">Pending</option>
            <option value="reviewed">Reviewed</option>
            <option value="shortlisted">Shortlisted</option>
            <option value="hired">Hired</option>
            <option value="rejected">Rejected</option>
          </select>
          <select
            value={`${sortBy}-${sortOrder}`}
            onChange={(e) => {
              const [by, order] = e.target.value.split("-");
              setSortBy(by as "date" | "score");
              setSortOrder(order as "asc" | "desc");
            }}
            className="px-3 py-2 border border-border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
          >
            <option value="score-desc">Highest Match</option>
            <option value="score-asc">Lowest Match</option>
            <option value="date-desc">Newest First</option>
            <option value="date-asc">Oldest First</option>
          </select>
        </div>
      </div>

      {/* Applications List */}
      {filteredApplications.length === 0 ? (
        <div className="bg-card rounded-xl border border-border p-12 text-center">
          <div className="w-16 h-16 bg-muted rounded-full flex items-center justify-center mx-auto mb-4">
            <Search className="w-8 h-8 text-muted-foreground" />
          </div>
          <h3 className="text-lg font-medium mb-2">No candidates found</h3>
          <p className="text-muted-foreground">
            {searchQuery || statusFilter !== "all"
              ? "Try adjusting your search or filter"
              : "Applications will appear here when candidates apply to your jobs"}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {filteredApplications.map((app) => {
            // FIX: Validate match_score cho mỗi application
            const validScore = validateMatchScore(app.match_score);
            const scorePercentage = validScore;
            const scoreColor = getScoreColor(scorePercentage);
            // Tính toán stroke dasharray cho circle (0-100 -> 0-176)
            const strokeDasharray = (scorePercentage / 100) * 176;

            return (
              <div
                key={app.id}
                className="bg-card rounded-xl border border-border overflow-hidden"
              >
                {/* Main Row */}
                <div
                  className="p-6 cursor-pointer hover:bg-muted/30 transition-colors"
                  onClick={() =>
                    setExpandedId(expandedId === app.id ? null : app.id)
                  }
                >
                  <div className="flex items-center gap-4">
                    {/* Avatar */}
                    <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center flex-shrink-0">
                      <span className="text-lg font-semibold text-primary">
                        {app.candidate?.full_name?.[0]?.toUpperCase() ||
                          app.candidate?.email?.[0]?.toUpperCase() ||
                          "C"}
                      </span>
                    </div>

                    {/* Info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <h3 className="font-semibold truncate">
                          {app.candidate?.full_name ||
                            app.candidate?.email?.split("@")[0] ||
                            "Unknown Candidate"}
                        </h3>
                        <span
                          className={`px-2 py-0.5 rounded-full text-xs font-medium capitalize ${getStatusColor(
                            app.status,
                          )}`}
                        >
                          {getStatusLabel(app.status)}
                        </span>
                      </div>
                      <p className="text-sm text-muted-foreground truncate">
                        Applied for{" "}
                        <span className="font-medium text-foreground">
                          {app.job?.title || "Unknown Job"}
                        </span>
                        {app.job?.company && ` at ${app.job.company}`}
                      </p>
                      <p className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {new Date(app.created_at).toLocaleDateString()}
                      </p>
                    </div>

                    {/* Match Score - FIXED */}
                    {app.match_score !== undefined && (
                      <div className="flex items-center gap-3">
                        <div className="text-right">
                          <p className="text-2xl font-bold">
                            {scorePercentage}%
                          </p>
                          <p className="text-xs text-muted-foreground">
                            Match Score
                          </p>
                        </div>
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
                        </div>
                      </div>
                    )}

                    {/* Expand Icon */}
                    <div className="ml-2">
                      {expandedId === app.id ? (
                        <ChevronUp className="w-5 h-5 text-muted-foreground" />
                      ) : (
                        <ChevronDown className="w-5 h-5 text-muted-foreground" />
                      )}
                    </div>
                  </div>
                </div>

                {/* Expanded Details */}
                {expandedId === app.id && (
                  <div className="border-t border-border p-6 bg-muted/20">
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                      {/* Skills Analysis */}
                      {app.matched_skills && app.matched_skills.length > 0 && (
                        <div>
                          <h4 className="font-medium mb-3 flex items-center gap-2">
                            <Check className="w-4 h-4 text-emerald-600" />
                            Matched Skills ({app.matched_skills.length})
                          </h4>
                          <div className="flex flex-wrap gap-2">
                            {app.matched_skills.map((skill) => (
                              <span
                                key={skill}
                                className="px-2 py-1 bg-emerald-500/10 text-emerald-600 rounded-md text-sm"
                              >
                                {skill}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {app.missing_skills && app.missing_skills.length > 0 && (
                        <div>
                          <h4 className="font-medium mb-3 flex items-center gap-2">
                            <X className="w-4 h-4 text-amber-600" />
                            Missing Skills ({app.missing_skills.length})
                          </h4>
                          <div className="flex flex-wrap gap-2">
                            {app.missing_skills.map((skill) => (
                              <span
                                key={skill}
                                className="px-2 py-1 bg-amber-500/10 text-amber-600 rounded-md text-sm"
                              >
                                {skill}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Cover Letter */}
                    {app.cover_letter && (
                      <div className="mt-6">
                        <h4 className="font-medium mb-2">Cover Letter</h4>
                        <p className="text-sm text-muted-foreground bg-card rounded-lg p-4 border border-border whitespace-pre-wrap">
                          {app.cover_letter}
                        </p>
                      </div>
                    )}

                    {/* Recruiter Notes */}
                    {app.recruiter_notes && (
                      <div className="mt-6">
                        <h4 className="font-medium mb-2">Recruiter Notes</h4>
                        <p className="text-sm text-muted-foreground bg-card rounded-lg p-4 border border-border">
                          {app.recruiter_notes}
                        </p>
                      </div>
                    )}

                    {/* Actions */}
                    <div className="mt-6 flex flex-wrap items-center gap-3">
                      {app.candidate?.email && (
                        <a
                          href={`mailto:${app.candidate.email}`}
                          className="inline-flex items-center gap-2 px-4 py-2 border border-border rounded-lg text-sm font-medium hover:bg-muted transition-colors"
                        >
                          <Mail className="w-4 h-4" />
                          Contact Candidate
                        </a>
                      )}
                      <div className="flex-1"></div>
                      {updatingStatus === app.id ? (
                        <div className="text-muted-foreground">Updating...</div>
                      ) : (
                        <>
                          {app.status === "pending" && (
                            <>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  updateApplicationStatus(app.id, "reviewed");
                                }}
                                className="inline-flex items-center gap-2 px-4 py-2 bg-amber-500 text-white rounded-lg text-sm font-medium hover:bg-amber-600 transition-colors"
                              >
                                <Star className="w-4 h-4" />
                                Mark as Reviewed
                              </button>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  updateApplicationStatus(
                                    app.id,
                                    "shortlisted",
                                  );
                                }}
                                className="inline-flex items-center gap-2 px-4 py-2 bg-purple-500 text-white rounded-lg text-sm font-medium hover:bg-purple-600 transition-colors"
                              >
                                <Star className="w-4 h-4" />
                                Shortlist
                              </button>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  updateApplicationStatus(app.id, "rejected");
                                }}
                                className="inline-flex items-center gap-2 px-4 py-2 border border-red-200 text-red-600 rounded-lg text-sm font-medium hover:bg-red-50 transition-colors"
                              >
                                <X className="w-4 h-4" />
                                Reject
                              </button>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  updateApplicationStatus(app.id, "hired");
                                }}
                                className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-500 text-white rounded-lg text-sm font-medium hover:bg-emerald-600 transition-colors"
                              >
                                <Check className="w-4 h-4" />
                                Hire
                              </button>
                            </>
                          )}
                          {app.status === "reviewed" && (
                            <>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  updateApplicationStatus(
                                    app.id,
                                    "shortlisted",
                                  );
                                }}
                                className="inline-flex items-center gap-2 px-4 py-2 bg-purple-500 text-white rounded-lg text-sm font-medium hover:bg-purple-600 transition-colors"
                              >
                                <Star className="w-4 h-4" />
                                Shortlist
                              </button>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  updateApplicationStatus(app.id, "rejected");
                                }}
                                className="inline-flex items-center gap-2 px-4 py-2 border border-red-200 text-red-600 rounded-lg text-sm font-medium hover:bg-red-50 transition-colors"
                              >
                                <X className="w-4 h-4" />
                                Reject
                              </button>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  updateApplicationStatus(app.id, "hired");
                                }}
                                className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-500 text-white rounded-lg text-sm font-medium hover:bg-emerald-600 transition-colors"
                              >
                                <Check className="w-4 h-4" />
                                Hire
                              </button>
                            </>
                          )}
                          {app.status === "shortlisted" && (
                            <>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  updateApplicationStatus(app.id, "rejected");
                                }}
                                className="inline-flex items-center gap-2 px-4 py-2 border border-red-200 text-red-600 rounded-lg text-sm font-medium hover:bg-red-50 transition-colors"
                              >
                                <X className="w-4 h-4" />
                                Reject
                              </button>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  updateApplicationStatus(app.id, "hired");
                                }}
                                className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-500 text-white rounded-lg text-sm font-medium hover:bg-emerald-600 transition-colors"
                              >
                                <Check className="w-4 h-4" />
                                Hire
                              </button>
                            </>
                          )}
                        </>
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
