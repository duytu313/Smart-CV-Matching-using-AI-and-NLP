"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { api, Job } from "@/lib/api";
import {
  Plus,
  Search,
  Filter,
  MoreVertical,
  MapPin,
  Building,
  Calendar,
  Users,
  Pencil,
  Trash2,
  Eye,
  EyeOff,
  RefreshCw,
  AlertCircle,
} from "lucide-react";

export default function RecruiterJobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [filter, setFilter] = useState<"all" | "active" | "inactive">("all");
  const [openMenu, setOpenMenu] = useState<number | null>(null);
  const [updatingJob, setUpdatingJob] = useState<number | null>(null);

  useEffect(() => {
    loadJobs();
  }, []);

  async function loadJobs() {
    try {
      setIsLoading(true);
      setError(null);

      // Lấy user hiện tại
      const currentUser = await api.auth.me();
      console.log("Current user:", currentUser);

      // Lấy tất cả jobs
      const response = await api.jobs.list({ page: 1, page_size: 100 });
      const allJobs = response.jobs || [];
      console.log("All jobs:", allJobs);

      // Lọc jobs theo recruiter_id của user hiện tại
      const myJobs = allJobs.filter(
        (job) => job.recruiter_id === currentUser.id,
      );
      console.log("My jobs:", myJobs);

      setJobs(myJobs);
    } catch (error) {
      console.error("Failed to load jobs:", error);
      setError(error instanceof Error ? error.message : "Failed to load jobs");
    } finally {
      setIsLoading(false);
    }
  }

  async function toggleJobStatus(jobId: number, isActive: boolean) {
    try {
      setUpdatingJob(jobId);
      await api.jobs.update(jobId, { is_active: !isActive });
      setJobs(
        jobs.map((j) => (j.id === jobId ? { ...j, is_active: !isActive } : j)),
      );
      setOpenMenu(null);
    } catch (error) {
      console.error("Failed to update job:", error);
      setError(
        error instanceof Error ? error.message : "Failed to update job status",
      );
    } finally {
      setUpdatingJob(null);
    }
  }

  async function deleteJob(jobId: number) {
    if (
      !confirm(
        "Are you sure you want to delete this job posting? This action cannot be undone.",
      )
    )
      return;
    try {
      setUpdatingJob(jobId);
      await api.jobs.delete(jobId);
      setJobs(jobs.filter((j) => j.id !== jobId));
      setOpenMenu(null);
    } catch (error) {
      console.error("Failed to delete job:", error);
      setError(error instanceof Error ? error.message : "Failed to delete job");
    } finally {
      setUpdatingJob(null);
    }
  }

  const filteredJobs = jobs.filter((job) => {
    const matchesSearch =
      job.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      job.company?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      job.location?.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesFilter =
      filter === "all" ||
      (filter === "active" && job.is_active) ||
      (filter === "inactive" && !job.is_active);
    return matchesSearch && matchesFilter;
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="space-y-4">
          {[...Array(3)].map((_, i) => (
            <div
              key={i}
              className="bg-card rounded-xl border border-border p-6 animate-pulse"
            >
              <div className="h-6 w-48 bg-muted rounded mb-3"></div>
              <div className="h-4 w-32 bg-muted rounded mb-4"></div>
              <div className="h-16 w-full bg-muted rounded"></div>
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
          <p className="text-red-600 mb-2">Error loading jobs</p>
          <p className="text-sm text-red-500 mb-4">{error}</p>
          <button
            onClick={loadJobs}
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
          <h1 className="text-2xl font-bold">My Job Postings</h1>
          <p className="text-muted-foreground mt-1">
            Manage and track your job listings
          </p>
        </div>
        <Link
          href="/recruiter/jobs/new"
          className="inline-flex items-center justify-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Post New Job
        </Link>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search jobs by title, company, or location..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-muted-foreground" />
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value as typeof filter)}
            className="px-3 py-2 border border-border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
          >
            <option value="all">All Jobs</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
        </div>
      </div>

      {/* Jobs List */}
      {filteredJobs.length === 0 ? (
        <div className="bg-card rounded-xl border border-border p-12 text-center">
          <div className="w-16 h-16 bg-muted rounded-full flex items-center justify-center mx-auto mb-4">
            <Search className="w-8 h-8 text-muted-foreground" />
          </div>
          <h3 className="text-lg font-medium mb-2">No jobs found</h3>
          <p className="text-muted-foreground mb-6">
            {searchQuery || filter !== "all"
              ? "Try adjusting your search or filter"
              : "Start by posting your first job"}
          </p>
          {!searchQuery && filter === "all" && (
            <Link
              href="/recruiter/jobs/new"
              className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90"
            >
              <Plus className="w-4 h-4" />
              Post Your First Job
            </Link>
          )}
        </div>
      ) : (
        <div className="space-y-4">
          {filteredJobs.map((job) => (
            <div
              key={job.id}
              className="bg-card rounded-xl border border-border p-6 hover:shadow-lg transition-shadow"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2 flex-wrap">
                    <h3 className="text-lg font-semibold">{job.title}</h3>
                    <span
                      className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                        job.is_active
                          ? "bg-emerald-500/10 text-emerald-600"
                          : "bg-muted text-muted-foreground"
                      }`}
                    >
                      {job.is_active ? "Active" : "Inactive"}
                    </span>
                    {job.job_type && (
                      <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-blue-500/10 text-blue-600">
                        {job.job_type}
                      </span>
                    )}
                  </div>
                  <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground mb-4">
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
                    <span className="flex items-center gap-1">
                      <Calendar className="w-4 h-4" />
                      Posted {new Date(job.created_at).toLocaleDateString()}
                    </span>
                    <span className="flex items-center gap-1">
                      <Users className="w-4 h-4" />
                      {job.applications_count || 0} applications
                    </span>
                    <span className="flex items-center gap-1">
                      <Eye className="w-4 h-4" />
                      {job.views_count || 0} views
                    </span>
                  </div>
                  <p className="text-muted-foreground line-clamp-2">
                    {job.description}
                  </p>
                  {job.required_skills && job.required_skills.length > 0 && (
                    <div className="flex flex-wrap gap-2 mt-4">
                      {job.required_skills.slice(0, 5).map((skill) => (
                        <span
                          key={skill}
                          className="px-2 py-1 bg-muted rounded-md text-xs font-medium"
                        >
                          {skill}
                        </span>
                      ))}
                      {job.required_skills.length > 5 && (
                        <span className="px-2 py-1 text-xs text-muted-foreground">
                          +{job.required_skills.length - 5} more
                        </span>
                      )}
                    </div>
                  )}
                </div>
                <div className="relative ml-4">
                  <button
                    onClick={() =>
                      setOpenMenu(openMenu === job.id ? null : job.id)
                    }
                    className="p-2 hover:bg-muted rounded-lg transition-colors"
                    disabled={updatingJob === job.id}
                  >
                    <MoreVertical className="w-5 h-5" />
                  </button>
                  {openMenu === job.id && (
                    <div className="absolute right-0 top-full mt-1 w-48 bg-card border border-border rounded-lg shadow-lg z-10">
                      <Link
                        href={`/recruiter/jobs/${job.id}`}
                        className="flex items-center gap-2 px-4 py-2 hover:bg-muted transition-colors text-sm"
                        onClick={() => setOpenMenu(null)}
                      >
                        <Eye className="w-4 h-4" />
                        View Details
                      </Link>
                      <Link
                        href={`/recruiter/jobs/${job.id}/edit`}
                        className="flex items-center gap-2 px-4 py-2 hover:bg-muted transition-colors text-sm"
                        onClick={() => setOpenMenu(null)}
                      >
                        <Pencil className="w-4 h-4" />
                        Edit Job
                      </Link>
                      <button
                        onClick={() => toggleJobStatus(job.id, job.is_active)}
                        className="flex items-center gap-2 px-4 py-2 hover:bg-muted transition-colors text-sm w-full"
                        disabled={updatingJob === job.id}
                      >
                        {job.is_active ? (
                          <>
                            <EyeOff className="w-4 h-4" />
                            Deactivate
                          </>
                        ) : (
                          <>
                            <Eye className="w-4 h-4" />
                            Activate
                          </>
                        )}
                      </button>
                      <button
                        onClick={() => deleteJob(job.id)}
                        className="flex items-center gap-2 px-4 py-2 hover:bg-muted transition-colors text-sm w-full text-red-600"
                        disabled={updatingJob === job.id}
                      >
                        <Trash2 className="w-4 h-4" />
                        Delete
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
