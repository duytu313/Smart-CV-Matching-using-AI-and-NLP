"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { api, Job, Application } from "@/lib/api";
import {
  Briefcase,
  Users,
  Eye,
  TrendingUp,
  ArrowRight,
  Clock,
  MapPin,
  Building,
  PlusCircle,
  AlertCircle,
  RefreshCw,
} from "lucide-react";

interface DashboardStats {
  totalJobs: number;
  activeJobs: number;
  totalApplications: number;
  newApplications: number;
}

// Helper function để validate match_score
function validateMatchScore(score: number | undefined): number {
  if (!score || isNaN(score)) return 0;
  // Nếu score > 1, coi như nó là percentage (0-100)
  if (score > 1) {
    // Nếu score > 100, clamp về 100
    return Math.min(Math.max(Math.round(score), 0), 100);
  }
  // Nếu score <= 1, coi như decimal (0-1), convert sang percentage
  return Math.min(Math.max(Math.round(score * 100), 0), 100);
}

// Helper function để lấy màu sắc cho match score
function getMatchScoreColor(score: number): string {
  if (score >= 80) return "text-emerald-600";
  if (score >= 60) return "text-amber-600";
  return "text-red-600";
}

export default function RecruiterDashboard() {
  const [stats, setStats] = useState<DashboardStats>({
    totalJobs: 0,
    activeJobs: 0,
    totalApplications: 0,
    newApplications: 0,
  });
  const [recentJobs, setRecentJobs] = useState<Job[]>([]);
  const [recentApplications, setRecentApplications] = useState<Application[]>(
    [],
  );
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentUser, setCurrentUser] = useState<any>(null);

  useEffect(() => {
    loadUserAndData();
  }, []);

  async function loadUserAndData() {
    try {
      setIsLoading(true);
      setError(null);

      // Get current user
      const user = await api.auth.me();
      setCurrentUser(user);
      console.log("Current user:", user);

      await loadDashboardData(user);
    } catch (err) {
      console.error("Failed to load user:", err);
      setError(err instanceof Error ? err.message : "Failed to load user data");
      setIsLoading(false);
    }
  }

  async function loadDashboardData(user: any) {
    try {
      // Lấy tất cả jobs
      const jobsResponse = await api.jobs.list({ page: 1, page_size: 100 });
      const allJobs = jobsResponse.jobs || [];
      console.log("All jobs:", allJobs.length);

      // Lọc jobs theo recruiter_id của user hiện tại
      const myJobs = allJobs.filter((job) => job.recruiter_id === user?.id);
      console.log("My jobs:", myJobs.length);

      const activeJobs = myJobs.filter((job) => job.is_active);

      // Lấy tất cả applications
      let allApplications: Application[] = [];
      try {
        allApplications = await api.applications.list();
        console.log("All applications:", allApplications.length);
      } catch (err) {
        console.log("Could not fetch applications:", err);
        allApplications = [];
      }

      // Lọc applications cho jobs của recruiter này
      const myJobIds = new Set(myJobs.map((job) => job.id));
      const myApplications = allApplications.filter((app) =>
        myJobIds.has(app.job_id),
      );
      console.log("My applications:", myApplications.length);

      // Applications mới (pending status)
      const newApplications = myApplications.filter(
        (app) => app.status === "pending",
      );

      // Cập nhật stats
      setStats({
        totalJobs: myJobs.length,
        activeJobs: activeJobs.length,
        totalApplications: myApplications.length,
        newApplications: newApplications.length,
      });

      // Lấy 5 jobs gần nhất
      const sortedJobs = [...myJobs].sort(
        (a, b) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
      );
      setRecentJobs(sortedJobs.slice(0, 5));

      // Lấy 5 applications gần nhất và validate match_score
      const sortedApps = [...myApplications].sort(
        (a, b) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
      );

      // Validate match_score cho mỗi application
      const validatedApps = sortedApps.slice(0, 5).map((app) => ({
        ...app,
        match_score: validateMatchScore(app.match_score),
      }));

      setRecentApplications(validatedApps);
    } catch (error) {
      console.error("Failed to load dashboard data:", error);
      setError(
        error instanceof Error
          ? error.message
          : "Failed to load dashboard data",
      );
    } finally {
      setIsLoading(false);
    }
  }

  const statCards = [
    {
      label: "Total Jobs",
      value: stats.totalJobs,
      icon: Briefcase,
      color: "bg-primary/10 text-primary",
      href: "/recruiter/jobs",
    },
    {
      label: "Active Jobs",
      value: stats.activeJobs,
      icon: TrendingUp,
      color: "bg-emerald-500/10 text-emerald-600",
      href: "/recruiter/jobs?status=active",
    },
    {
      label: "Total Applications",
      value: stats.totalApplications,
      icon: Users,
      color: "bg-blue-500/10 text-blue-600",
      href: "/recruiter/candidates",
    },
    {
      label: "New Applications",
      value: stats.newApplications,
      icon: Eye,
      color: "bg-amber-500/10 text-amber-600",
      href: "/recruiter/candidates?status=pending",
    },
  ];

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-card rounded-xl p-6 animate-pulse">
              <div className="h-12 w-12 bg-muted rounded-lg mb-4"></div>
              <div className="h-4 w-16 bg-muted rounded mb-2"></div>
              <div className="h-8 w-24 bg-muted rounded"></div>
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
          <p className="text-red-600 mb-2">Error loading dashboard</p>
          <p className="text-sm text-red-500 mb-4">{error}</p>
          <button
            onClick={() => loadUserAndData()}
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
    <div className="space-y-8">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">Recruiter Dashboard</h1>
          <p className="text-muted-foreground mt-1">
            Manage your job postings and review candidates
          </p>
        </div>
        <Link
          href="/recruiter/jobs/new"
          className="px-4 py-2 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 transition-colors flex items-center gap-2"
        >
          <PlusCircle className="w-4 h-4" />
          Post New Job
        </Link>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((stat) => (
          <Link
            key={stat.label}
            href={stat.href}
            className="bg-card rounded-xl border border-border p-6 hover:shadow-lg transition-all hover:border-primary/50"
          >
            <div
              className={`w-12 h-12 rounded-lg ${stat.color} flex items-center justify-center mb-4`}
            >
              <stat.icon className="w-6 h-6" />
            </div>
            <p className="text-sm text-muted-foreground">{stat.label}</p>
            <p className="text-3xl font-bold mt-1">{stat.value}</p>
          </Link>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Jobs */}
        <div className="bg-card rounded-xl border border-border">
          <div className="p-6 border-b border-border flex items-center justify-between">
            <h2 className="text-lg font-semibold">Recent Job Postings</h2>
            <Link
              href="/recruiter/jobs"
              className="text-sm text-primary hover:underline flex items-center gap-1"
            >
              View all <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
          <div className="divide-y divide-border">
            {recentJobs.length === 0 ? (
              <div className="p-8 text-center">
                <Briefcase className="w-12 h-12 text-muted-foreground/50 mx-auto mb-3" />
                <p className="text-muted-foreground">No jobs posted yet</p>
                <Link
                  href="/recruiter/jobs/new"
                  className="inline-block mt-4 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90"
                >
                  Post Your First Job
                </Link>
              </div>
            ) : (
              recentJobs.map((job) => (
                <Link
                  key={job.id}
                  href={`/recruiter/jobs/${job.id}`}
                  className="block p-4 hover:bg-muted/50 transition-colors"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h3 className="font-medium hover:text-primary transition-colors">
                        {job.title}
                      </h3>
                      <div className="flex items-center gap-4 mt-1 text-sm text-muted-foreground flex-wrap">
                        {job.company && (
                          <span className="flex items-center gap-1">
                            <Building className="w-3 h-3" />
                            {job.company}
                          </span>
                        )}
                        {job.location && (
                          <span className="flex items-center gap-1">
                            <MapPin className="w-3 h-3" />
                            {job.location}
                          </span>
                        )}
                        {job.job_type && (
                          <span className="flex items-center gap-1">
                            <Briefcase className="w-3 h-3" />
                            {job.job_type}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                        <span className="flex items-center gap-1">
                          <Users className="w-3 h-3" />
                          {job.applications_count || 0} applications
                        </span>
                        <span className="flex items-center gap-1">
                          <Eye className="w-3 h-3" />
                          {job.views_count || 0} views
                        </span>
                      </div>
                    </div>
                    <span
                      className={`px-2 py-1 rounded-full text-xs font-medium ${
                        job.is_active
                          ? "bg-emerald-500/10 text-emerald-600"
                          : "bg-muted text-muted-foreground"
                      }`}
                    >
                      {job.is_active ? "Active" : "Inactive"}
                    </span>
                  </div>
                </Link>
              ))
            )}
          </div>
        </div>

        {/* Recent Applications */}
        <div className="bg-card rounded-xl border border-border">
          <div className="p-6 border-b border-border flex items-center justify-between">
            <h2 className="text-lg font-semibold">Recent Applications</h2>
            <Link
              href="/recruiter/candidates"
              className="text-sm text-primary hover:underline flex items-center gap-1"
            >
              View all <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
          <div className="divide-y divide-border">
            {recentApplications.length === 0 ? (
              <div className="p-8 text-center">
                <Users className="w-12 h-12 text-muted-foreground/50 mx-auto mb-3" />
                <p className="text-muted-foreground">No applications yet</p>
                <p className="text-sm text-muted-foreground mt-1">
                  Applications will appear here when candidates apply to your
                  jobs
                </p>
                {recentJobs.length > 0 && (
                  <p className="text-sm text-muted-foreground mt-2">
                    Share your job posts to attract candidates
                  </p>
                )}
              </div>
            ) : (
              recentApplications.map((app) => {
                // Validate match_score cho mỗi application
                const validMatchScore = validateMatchScore(app.match_score);
                const matchScoreColor = getMatchScoreColor(validMatchScore);

                return (
                  <Link
                    key={app.id}
                    href={`/recruiter/candidates/${app.id}`}
                    className="block p-4 hover:bg-muted/50 transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3 flex-1">
                        <div className="w-10 h-10 bg-primary/10 rounded-full flex items-center justify-center flex-shrink-0">
                          <span className="text-sm font-medium text-primary">
                            {app.candidate?.full_name?.[0]?.toUpperCase() ||
                              app.candidate?.email?.[0]?.toUpperCase() ||
                              "C"}
                          </span>
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="font-medium truncate">
                            {app.candidate?.full_name ||
                              app.candidate?.email?.split("@")[0] ||
                              "Candidate"}
                          </p>
                          <p className="text-sm text-muted-foreground truncate">
                            Applied to {app.job?.title || "Job"}
                          </p>
                          {app.cover_letter && (
                            <p className="text-xs text-muted-foreground mt-1 line-clamp-1">
                              {app.cover_letter.substring(0, 100)}
                            </p>
                          )}
                        </div>
                      </div>
                      <div className="text-right ml-4">
                        {app.match_score !== undefined && (
                          <div className="flex items-center gap-2 mb-1">
                            <span
                              className={`text-sm font-medium ${matchScoreColor}`}
                            >
                              {validMatchScore}% match
                            </span>
                          </div>
                        )}
                        <div className="flex items-center gap-1 text-xs text-muted-foreground">
                          <Clock className="w-3 h-3" />
                          {new Date(app.created_at).toLocaleDateString()}
                        </div>
                        <span
                          className={`inline-block mt-1 px-2 py-0.5 rounded-full text-xs font-medium ${
                            app.status === "pending"
                              ? "bg-amber-500/10 text-amber-600"
                              : app.status === "reviewed"
                                ? "bg-blue-500/10 text-blue-600"
                                : app.status === "shortlisted"
                                  ? "bg-purple-500/10 text-purple-600"
                                  : app.status === "hired"
                                    ? "bg-emerald-500/10 text-emerald-600"
                                    : "bg-red-500/10 text-red-600"
                          }`}
                        >
                          {app.status}
                        </span>
                      </div>
                    </div>
                  </Link>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
