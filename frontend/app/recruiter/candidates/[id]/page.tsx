// app/recruiter/candidates/[id]/page.tsx
"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, User, Application } from "@/lib/api";
import {
  ArrowLeft,
  Mail,
  Phone,
  MapPin,
  Briefcase,
  GraduationCap,
  Star,
  Clock,
  CheckCircle,
  XCircle,
  Eye,
  MessageSquare,
} from "lucide-react";

export default function CandidateDetailPage() {
  const params = useParams();
  const candidateId = params?.id as string;

  const [candidate, setCandidate] = useState<User | null>(null);
  const [applications, setApplications] = useState<Application[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (candidateId) {
      loadCandidateData();
    }
  }, [candidateId]);

  async function loadCandidateData() {
    try {
      setIsLoading(true);
      setError(null);

      // Lấy thông tin candidate
      // Note: Bạn cần có API endpoint để lấy thông tin candidate theo ID
      // Nếu chưa có, bạn có thể gọi /api/users/{id}
      const userResponse = await fetch(
        `http://localhost:8000/api/users/${candidateId}`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("auth_token")}`,
          },
        },
      );

      if (!userResponse.ok) {
        throw new Error("Candidate not found");
      }

      const userData = await userResponse.json();
      setCandidate(userData);

      // Lấy applications của candidate này
      const allApplications = await api.applications.list();
      const candidateApps = allApplications.filter(
        (app) => app.candidate_id === parseInt(candidateId),
      );

      // Enrich với job details
      const enrichedApps = await Promise.all(
        candidateApps.map(async (app) => {
          if (app.job_id && !app.job) {
            try {
              const job = await api.jobs.get(app.job_id);
              return { ...app, job };
            } catch {
              return app;
            }
          }
          return app;
        }),
      );

      setApplications(enrichedApps);
    } catch (error) {
      console.error("Failed to load candidate:", error);
      setError(
        error instanceof Error ? error.message : "Failed to load candidate",
      );
    } finally {
      setIsLoading(false);
    }
  }

  function getStatusBadge(status: string) {
    switch (status) {
      case "shortlisted":
        return {
          icon: CheckCircle,
          color: "bg-emerald-500/10 text-emerald-600",
          label: "Shortlisted",
        };
      case "hired":
        return {
          icon: CheckCircle,
          color: "bg-emerald-500/10 text-emerald-600",
          label: "Hired",
        };
      case "rejected":
        return {
          icon: XCircle,
          color: "bg-red-500/10 text-red-600",
          label: "Rejected",
        };
      case "reviewed":
        return {
          icon: Eye,
          color: "bg-amber-500/10 text-amber-600",
          label: "Reviewed",
        };
      default:
        return {
          icon: Clock,
          color: "bg-blue-500/10 text-blue-600",
          label: "Pending",
        };
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="animate-pulse">
          <div className="h-8 w-48 bg-muted rounded mb-4"></div>
          <div className="h-32 bg-muted rounded-lg mb-6"></div>
          <div className="h-64 bg-muted rounded-lg"></div>
        </div>
      </div>
    );
  }

  if (error || !candidate) {
    return (
      <div className="space-y-6">
        <Link
          href="/recruiter/candidates"
          className="inline-flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors mb-6"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Candidates
        </Link>
        <div className="bg-red-50 border border-red-200 rounded-lg p-12 text-center">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <XCircle className="w-8 h-8 text-red-600" />
          </div>
          <h3 className="text-lg font-medium text-red-600 mb-2">
            Candidate Not Found
          </h3>
          <p className="text-red-500 mb-6">
            {error || "The candidate you're looking for doesn't exist."}
          </p>
          <Link
            href="/recruiter/candidates"
            className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
          >
            View All Candidates
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Back Button */}
      <Link
        href="/recruiter/candidates"
        className="inline-flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Candidates
      </Link>

      {/* Candidate Profile */}
      <div className="bg-card rounded-xl border border-border p-6">
        <div className="flex items-start gap-6">
          <div className="w-24 h-24 bg-gradient-to-br from-primary/20 to-primary/10 rounded-full flex items-center justify-center">
            <span className="text-3xl font-bold text-primary">
              {candidate.full_name.charAt(0)}
            </span>
          </div>
          <div className="flex-1">
            <h1 className="text-2xl font-bold">{candidate.full_name}</h1>
            <p className="text-muted-foreground">{candidate.email}</p>

            <div className="flex flex-wrap gap-4 mt-4">
              {candidate.company_name && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Briefcase className="w-4 h-4" />
                  {candidate.company_name}
                </div>
              )}
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Mail className="w-4 h-4" />
                {candidate.email}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Applications */}
      <div>
        <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
          <Briefcase className="w-5 h-5" />
          Job Applications ({applications.length})
        </h2>

        {applications.length === 0 ? (
          <div className="bg-card rounded-xl border border-border p-12 text-center">
            <p className="text-muted-foreground">No applications yet</p>
          </div>
        ) : (
          <div className="space-y-4">
            {applications.map((app) => {
              const status = getStatusBadge(app.status);
              const StatusIcon = status.icon;

              return (
                <div
                  key={app.id}
                  className="bg-card rounded-xl border border-border p-6 hover:shadow-lg transition-shadow"
                >
                  <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-start justify-between mb-2">
                        <h3 className="text-lg font-semibold">
                          {app.job?.title || "Job Title"}
                        </h3>
                        <span
                          className={`px-3 py-1 rounded-full text-xs font-medium ${status.color}`}
                        >
                          <StatusIcon className="w-3 h-3 inline mr-1" />
                          {status.label}
                        </span>
                      </div>
                      <div className="text-sm text-muted-foreground mb-3">
                        {app.job?.company && (
                          <span className="flex items-center gap-1">
                            <Briefcase className="w-4 h-4" />
                            {app.job.company}
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground">
                        Applied on{" "}
                        {new Date(app.created_at).toLocaleDateString()}
                      </p>
                    </div>

                    {/* Match Score */}
                    {app.match_score && (
                      <div className="flex items-center gap-3 p-3 bg-muted/50 rounded-lg">
                        <div className="w-12 h-12 relative">
                          <svg className="w-12 h-12 -rotate-90">
                            <circle
                              cx="24"
                              cy="24"
                              r="20"
                              fill="none"
                              stroke="currentColor"
                              strokeWidth="3"
                              className="text-muted"
                            />
                            <circle
                              cx="24"
                              cy="24"
                              r="20"
                              fill="none"
                              stroke="currentColor"
                              strokeWidth="3"
                              strokeDasharray={`${(app.match_score / 100) * 125.6} 125.6`}
                              strokeLinecap="round"
                              className={
                                app.match_score >= 80
                                  ? "text-emerald-500"
                                  : app.match_score >= 60
                                    ? "text-amber-500"
                                    : "text-red-500"
                              }
                            />
                          </svg>
                          <div className="absolute inset-0 flex items-center justify-center">
                            <span className="text-xs font-bold">
                              {Math.round(app.match_score)}%
                            </span>
                          </div>
                        </div>
                        <div>
                          <p className="text-xs font-medium">Match Score</p>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Skills */}
                  {(app.matched_skills?.length ||
                    app.missing_skills?.length) && (
                    <div className="mt-4 pt-4 border-t border-border">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {app.matched_skills &&
                          app.matched_skills.length > 0 && (
                            <div>
                              <p className="text-sm font-medium mb-2 text-emerald-600">
                                ✓ Matched Skills ({app.matched_skills.length})
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
                              </div>
                            </div>
                          )}
                        {app.missing_skills &&
                          app.missing_skills.length > 0 && (
                            <div>
                              <p className="text-sm font-medium mb-2 text-amber-600">
                                ✗ Missing Skills ({app.missing_skills.length})
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
                              </div>
                            </div>
                          )}
                      </div>
                    </div>
                  )}

                  {/* Actions */}
                  <div className="mt-4 pt-4 border-t border-border flex justify-end gap-3">
                    <Link
                      href={`/recruiter/applications/${app.id}`}
                      className="px-4 py-2 text-sm font-medium text-primary hover:bg-primary/10 rounded-lg transition-colors"
                    >
                      View Application
                    </Link>
                    <Link
                      href={`/recruiter/messages?candidate=${candidate.id}`}
                      className="px-4 py-2 text-sm font-medium bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
                    >
                      <MessageSquare className="w-4 h-4 inline mr-1" />
                      Message
                    </Link>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
