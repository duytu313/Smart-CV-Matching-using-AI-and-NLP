/**
 * API client for the job recommendation backend.
 * Handles all HTTP requests to the FastAPI backend.
 */

// SỬA: Thay vì "/api", dùng full URL từ environment variable
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Token storage
let authToken: string | null = null;

export function setAuthToken(token: string | null) {
  authToken = token;
  if (typeof window !== "undefined") {
    if (token) {
      localStorage.setItem("auth_token", token);
      // Also set cookie for middleware
      document.cookie = `token=${token}; path=/; max-age=86400`; // 24 hours
    } else {
      localStorage.removeItem("auth_token");
      // Clear cookie
      document.cookie = "token=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT";
    }
  }
}

export function getAuthToken(): string | null {
  if (authToken) return authToken;
  if (typeof window !== "undefined") {
    authToken = localStorage.getItem("auth_token");
  }
  return authToken;
}

async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {},
): Promise<T> {
  const token = getAuthToken();

  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...options.headers,
  };

  if (token) {
    (headers as Record<string, string>)["Authorization"] = `Bearer ${token}`;
  }

  const url = `${API_BASE}${endpoint}`;
  console.log(`API Request: ${options.method || "GET"} ${url}`);
  console.log(`Headers:`, headers);

  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });

    console.log(`Response status: ${response.status} ${response.statusText}`);

    if (!response.ok) {
      let error;
      let message = "Request failed";

      // If unauthorized, clear token
      if (response.status === 401) {
        console.log("Unauthorized - clearing token");
        setAuthToken(null);
      }

      try {
        const responseText = await response.text();
        console.log(`Response text: ${responseText}`);

        if (responseText) {
          try {
            error = JSON.parse(responseText);
            console.error("Error response:", error);
          } catch (e) {
            error = responseText;
          }
        } else {
          error = { detail: `Empty response from server` };
        }

        if (typeof error === "string") {
          message = error;
        } else if (typeof error?.detail === "string") {
          message = error.detail;
        } else if (Array.isArray(error?.detail)) {
          message = error.detail.join(", ");
        } else if (typeof error?.detail === "object") {
          message = JSON.stringify(error.detail);
        } else if (typeof error?.message === "string") {
          message = error.message;
        } else if (error) {
          message = JSON.stringify(error);
        }
      } catch (e) {
        console.error("Error parsing response:", e);
        message = `HTTP ${response.status}: ${response.statusText}`;
      }

      const fullError = new Error(message);
      (fullError as any).status = response.status;
      (fullError as any).endpoint = endpoint;
      throw fullError;
    }

    const data = await response.json();
    console.log(`Response data:`, data);
    return data;
  } catch (error) {
    console.error(`API request failed for ${url}:`, error);
    throw error;
  }
}

// Helper function để validate match_score
function validateMatchScore(score: number): number {
  if (!score || isNaN(score)) return 0;
  // Nếu score > 1, coi như nó là percentage (0-100)
  if (score > 1) {
    // Nếu score > 100, clamp về 100
    return Math.min(Math.max(Math.round(score), 0), 100);
  }
  // Nếu score <= 1, coi như decimal (0-1), convert sang percentage
  return Math.min(Math.max(Math.round(score * 100), 0), 100);
}

// Helper function để kiểm tra file type
function isImageFile(file: File): boolean {
  const imageTypes = [
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/bmp",
    "image/tiff",
    "image/webp",
  ];
  const imageExtensions = [
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
    ".tiff",
    ".tif",
    ".webp",
  ];
  return (
    imageTypes.includes(file.type) ||
    imageExtensions.some((ext) => file.name.toLowerCase().endsWith(ext))
  );
}

function isDocumentFile(file: File): boolean {
  const docTypes = [
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
  ];
  const docExtensions = [".pdf", ".docx", ".txt"];
  return (
    docTypes.includes(file.type) ||
    docExtensions.some((ext) => file.name.toLowerCase().endsWith(ext))
  );
}

// Types
export interface User {
  id: number;
  email: string;
  full_name: string;
  role: "candidate" | "recruiter";
  company_name?: string;
  created_at: string;
}

export interface Resume {
  id: number;
  user_id: number;
  title: string;
  raw_text?: string;
  skills?: string[];
  experience_years?: number;
  education?: { degree: string; institution: string; year: string }[];
  is_primary: boolean;
  created_at: string;
  updated_at: string;
}

export interface Job {
  id: number;
  recruiter_id: number;
  title: string;
  company: string;
  location?: string;
  job_type?: string;
  salary_min?: number;
  salary_max?: number;
  description: string;
  requirements?: string;
  required_skills?: string[];
  preferred_skills?: string[];
  experience_min?: number;
  experience_max?: number;
  is_active: boolean;
  views_count: number;
  applications_count: number;
  created_at: string;
  updated_at: string;
}

export interface Application {
  id: number;
  candidate_id: number;
  job_id: number;
  resume_id?: number;
  status: "pending" | "reviewed" | "shortlisted" | "rejected" | "hired";
  cover_letter?: string;
  match_score?: number;
  matched_skills?: string[];
  missing_skills?: string[];
  recruiter_notes?: string;
  created_at: string;
  updated_at: string;
  job?: Job;
  candidate?: User;
}

export interface JobMatch {
  job_id: number;
  title: string;
  company: string;
  location?: string;
  match_score: number;
  matched_skills: string[];
  missing_skills: string[];
  skill_match_percentage: number;
  recommendation_reason: string;
  job_type?: string;
  salary_min?: number;
  salary_max?: number;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface CandidateDashboard {
  user: User;
  resumes: Resume[];
  applications: Application[];
  recommendations: JobMatch[];
  stats: {
    total_applications: number;
    pending_applications: number;
    shortlisted: number;
    resumes_count: number;
  };
}

export interface RecruiterDashboard {
  user: User;
  jobs: Job[];
  recent_applications: Application[];
  stats: {
    total_jobs: number;
    active_jobs: number;
    total_applications: number;
    total_views: number;
    pending_review: number;
  };
}

// Helper functions để tránh circular dependency
async function getMyJobsHelper(): Promise<{ jobs: Job[]; total: number }> {
  try {
    console.log("Fetching jobs for recruiter...");

    // Kiểm tra token trước
    const token = getAuthToken();
    if (!token) {
      console.error("No auth token found");
      return { jobs: [], total: 0 };
    }

    // Thử lấy user info trước để debug
    try {
      const currentUser = await auth.me();
      console.log("Current user:", currentUser);

      if (!currentUser || currentUser.role !== "recruiter") {
        console.log("User is not a recruiter or not found");
        return { jobs: [], total: 0 };
      }
    } catch (userError) {
      console.error("Failed to get current user:", userError);
      return { jobs: [], total: 0 };
    }

    // Thử endpoint /api/jobs trước
    const response = await apiRequest<{
      jobs?: Job[];
      total?: number;
      page?: number;
      page_size?: number;
      total_pages?: number;
    }>("/api/jobs?page=1&page_size=1000").catch(async (error) => {
      console.error(
        "Failed to fetch from /api/jobs, trying alternative endpoints...",
        error,
      );

      // Thử endpoint khác nếu có
      try {
        const altResponse = await apiRequest<any>("/api/jobs/me");
        console.log("Alternative response:", altResponse);
        return altResponse;
      } catch (altError) {
        console.error("Alternative endpoint also failed:", altError);
        throw error;
      }
    });

    console.log("Jobs response:", response);

    // Xử lý response với nhiều format khác nhau
    let jobsList: Job[] = [];
    if (response.jobs && Array.isArray(response.jobs)) {
      jobsList = response.jobs;
    } else if (Array.isArray(response)) {
      jobsList = response;
    } else if (response.data && Array.isArray(response.data)) {
      jobsList = response.data;
    } else {
      console.warn("Unexpected response format:", response);
      jobsList = [];
    }

    // Lấy user info để filter
    const currentUser = await auth.me().catch(() => null);

    if (currentUser && currentUser.role === "recruiter") {
      const myJobs = jobsList.filter(
        (job) => job.recruiter_id === currentUser.id,
      );
      console.log(
        `Found ${myJobs.length} jobs for recruiter ${currentUser.id}`,
      );
      return { jobs: myJobs, total: myJobs.length };
    }

    return { jobs: jobsList, total: jobsList.length };
  } catch (error) {
    console.error("Failed to fetch jobs:", error);
    return { jobs: [], total: 0 };
  }
}

async function getMyApplicationsHelper(): Promise<Application[]> {
  try {
    const allApps = await apiRequest<Application[]>("/api/applications");
    const currentUser = await auth.me().catch(() => null);

    if (currentUser && currentUser.role === "candidate") {
      return allApps.filter((app) => app.candidate_id === currentUser.id);
    }

    return allApps;
  } catch (error) {
    console.error("Failed to fetch applications:", error);
    return [];
  }
}

async function getRecruiterApplicationsHelper(): Promise<Application[]> {
  try {
    const allApps = await apiRequest<Application[]>("/api/applications");
    const currentUser = await auth.me().catch(() => null);

    if (currentUser && currentUser.role === "recruiter") {
      const myJobs = await getMyJobsHelper();
      const myJobIds = new Set(myJobs.jobs.map((job) => job.id));

      const myApps = allApps.filter((app) => myJobIds.has(app.job_id));

      const enrichedApps = myApps.map((app) => ({
        ...app,
        job: myJobs.jobs.find((j) => j.id === app.job_id),
      }));

      return enrichedApps;
    }

    return [];
  } catch (error) {
    console.error("Failed to fetch recruiter applications:", error);
    return [];
  }
}

// Auth API
export const auth = {
  register: (data: {
    email: string;
    password: string;
    full_name: string;
    role: "candidate" | "recruiter";
    company_name?: string;
  }) =>
    apiRequest<TokenResponse>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  login: (email: string, password: string) =>
    apiRequest<TokenResponse>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  me: () => apiRequest<User>("/api/auth/me"),

  // THÊM METHOD LOGOUT
  logout: async () => {
    try {
      // Try to call logout endpoint if it exists
      const token = getAuthToken();
      if (token) {
        try {
          await apiRequest("/api/auth/logout", {
            method: "POST",
          });
        } catch (error) {
          console.error("Logout API error (non-critical):", error);
        }
      }
    } finally {
      // Always clear token locally
      setAuthToken(null);
    }
  },
};

// Resume API
export const resumes = {
  list: () => apiRequest<Resume[]>("/api/resumes"),

  get: (id: number) => apiRequest<Resume>(`/api/resumes/${id}`),

  upload: async (file: File, title: string) => {
    // Validate file type trên client
    if (!isDocumentFile(file) && !isImageFile(file)) {
      throw new Error(
        "Unsupported file type. Please upload PDF, DOCX, TXT, or image files (PNG, JPG, JPEG, BMP, TIFF, WEBP)",
      );
    }

    const formData = new FormData();
    formData.append("file", file);

    const token = getAuthToken();
    const url = `${API_BASE}/api/upload-cv?title=${encodeURIComponent(title)}`;

    const response = await fetch(url, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    });

    if (!response.ok) {
      const error = await response
        .json()
        .catch(() => ({ detail: "Upload failed" }));
      throw new Error(error.detail || "Upload failed");
    }

    return response.json();
  },

  analyze: (resume_text: string) =>
    apiRequest<{
      skills: string[];
      skills_by_category: Record<string, string[]>;
      experience_years?: number;
      education: { degree: string; institution: string; year: string }[];
      contact_info: Record<string, string>;
      skill_suggestions: string[];
    }>("/api/analyze-cv", {
      method: "POST",
      body: JSON.stringify({ resume_text }),
    }),

  // FIXED: Set CV làm primary bằng PATCH method
  setPrimary: (id: number) =>
    apiRequest<Resume>(`/api/resumes/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ is_primary: true }),
    }),

  // THÊM METHOD DELETE RESUME
  delete: (id: number) =>
    apiRequest<{ message: string }>(`/api/resumes/${id}`, {
      method: "DELETE",
    }),
};

// Jobs API
export const jobs = {
  list: (params?: {
    page?: number;
    page_size?: number;
    search?: string;
    location?: string;
    job_type?: string;
  }) => {
    const searchParams = new URLSearchParams();
    if (params?.page) searchParams.set("page", params.page.toString());
    if (params?.page_size)
      searchParams.set("page_size", params.page_size.toString());
    if (params?.search) searchParams.set("search", params.search);
    if (params?.location) searchParams.set("location", params.location);
    if (params?.job_type) searchParams.set("job_type", params.job_type);

    return apiRequest<{
      jobs: Job[];
      total: number;
      page: number;
      page_size: number;
      total_pages: number;
    }>(`/api/jobs?${searchParams}`);
  },

  getMyJobs: getMyJobsHelper,

  get: (id: number) => apiRequest<Job>(`/api/jobs/${id}`),

  create: (data: Partial<Job>) =>
    apiRequest<Job>("/api/jobs", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  update: (id: number, data: Partial<Job>) =>
    apiRequest<Job>(`/api/jobs/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  delete: (id: number) =>
    apiRequest<{ message: string }>(`/api/jobs/${id}`, { method: "DELETE" }),
};

// Applications API
export const applications = {
  list: () => apiRequest<Application[]>("/api/applications"),

  getMyApplications: getMyApplicationsHelper,

  getRecruiterApplications: getRecruiterApplicationsHelper,

  apply: (job_id: number, resume_id?: number, cover_letter?: string) =>
    apiRequest<Application>("/api/apply", {
      method: "POST",
      body: JSON.stringify({ job_id, resume_id, cover_letter }),
    }),

  updateStatus: (id: number, status: string, recruiter_notes?: string) =>
    apiRequest<Application>(`/api/applications/${id}`, {
      method: "PUT",
      body: JSON.stringify({ status, recruiter_notes }),
    }),
};

// Recommendations API
export const recommendations = {
  getRecommendations: (params: {
    resume_id?: number;
    resume_text?: string;
    k?: number;
    min_score?: number;
  }) =>
    apiRequest<{
      recommendations: JobMatch[];
      total_jobs_searched: number;
      resume_skills: string[];
    }>("/api/recommend-jobs", {
      method: "POST",
      body: JSON.stringify(params),
    }).then((response) => {
      // Validate và fix match_score cho tất cả recommendations
      if (response.recommendations && Array.isArray(response.recommendations)) {
        response.recommendations = response.recommendations.map((rec) => ({
          ...rec,
          match_score: validateMatchScore(rec.match_score),
          skill_match_percentage: validateMatchScore(
            rec.skill_match_percentage,
          ),
        }));
      }
      return response;
    }),

  getMatchExplanation: (
    job_id: number,
    resume_id?: number,
    resume_text?: string,
  ) =>
    apiRequest<{
      job: { id: number; title: string; company: string };
      overall_score: number;
      semantic_similarity: number;
      skill_analysis: Record<string, unknown>;
      matched_skills_by_category: Record<string, string[]>;
      missing_skills_by_category: Record<string, string[]>;
      skill_suggestions: string[];
    }>("/api/match-explanation", {
      method: "POST",
      body: JSON.stringify({ job_id, resume_id, resume_text }),
    }).then((response) => {
      // Validate overall_score
      if (response.overall_score !== undefined) {
        response.overall_score = validateMatchScore(response.overall_score);
      }
      if (response.semantic_similarity !== undefined) {
        response.semantic_similarity = validateMatchScore(
          response.semantic_similarity,
        );
      }
      return response;
    }),
};

// Dashboard API
export const dashboard = {
  candidate: async (): Promise<CandidateDashboard> => {
    try {
      const user = await auth.me();
      const resumesList = await resumes.list();
      const applicationsList = await getMyApplicationsHelper();
      const primaryResume = resumesList.find((r) => r.is_primary);

      let recommendationsList: JobMatch[] = [];
      if (primaryResume) {
        try {
          const recs = await recommendations.getRecommendations({
            resume_id: primaryResume.id,
          });
          recommendationsList = recs.recommendations || [];
        } catch (error) {
          console.error("Failed to get recommendations:", error);
        }
      }

      const stats = {
        total_applications: applicationsList.length,
        pending_applications: applicationsList.filter(
          (a) => a.status === "pending",
        ).length,
        shortlisted: applicationsList.filter((a) => a.status === "shortlisted")
          .length,
        resumes_count: resumesList.length,
      };

      return {
        user,
        resumes: resumesList,
        applications: applicationsList,
        recommendations: recommendationsList,
        stats,
      };
    } catch (error) {
      console.error("Failed to load candidate dashboard:", error);
      throw error;
    }
  },

  recruiter: async (): Promise<RecruiterDashboard> => {
    try {
      console.log("Loading recruiter dashboard...");
      const user = await auth.me();
      console.log("User loaded:", user);

      const myJobsResponse = await getMyJobsHelper();
      console.log("Jobs response:", myJobsResponse);

      const jobsList = myJobsResponse.jobs;

      let allApplications: Application[] = [];
      try {
        allApplications = await apiRequest<Application[]>("/api/applications");
        console.log(`Loaded ${allApplications.length} applications`);
      } catch (error) {
        console.error("Failed to fetch applications:", error);
        allApplications = [];
      }

      const myJobIds = new Set(jobsList.map((job) => job.id));
      const recentApplications = allApplications
        .filter((app) => myJobIds.has(app.job_id))
        .slice(0, 10);

      const enrichedApps = recentApplications.map((app) => ({
        ...app,
        job: jobsList.find((job) => job.id === app.job_id),
      }));

      const stats = {
        total_jobs: jobsList.length,
        active_jobs: jobsList.filter((j) => j.is_active).length,
        total_applications: allApplications.filter((app) =>
          myJobIds.has(app.job_id),
        ).length,
        total_views: jobsList.reduce(
          (sum, job) => sum + (job.views_count || 0),
          0,
        ),
        pending_review: allApplications.filter(
          (app) => myJobIds.has(app.job_id) && app.status === "pending",
        ).length,
      };

      console.log("Dashboard stats:", stats);

      return {
        user,
        jobs: jobsList,
        recent_applications: enrichedApps,
        stats,
      };
    } catch (error) {
      console.error("Failed to load recruiter dashboard:", error);
      // Return default data instead of throwing
      const user = await auth.me().catch(() => null);
      return {
        user: user || {
          id: 0,
          email: "",
          full_name: "",
          role: "recruiter",
          created_at: "",
        },
        jobs: [],
        recent_applications: [],
        stats: {
          total_jobs: 0,
          active_jobs: 0,
          total_applications: 0,
          total_views: 0,
          pending_review: 0,
        },
      };
    }
  },
};

// Evaluation API
export const evaluation = {
  evaluate: (
    recommended_job_ids: number[],
    relevant_job_ids: number[],
    k: number = 10,
  ) =>
    apiRequest<{
      precision_at_k: number;
      recall_at_k: number;
      f1_at_k: number;
      ndcg_at_k: number;
      map_at_k: number;
      mrr: number;
      hit_rate: number;
      k: number;
      num_relevant: number;
      num_recommended: number;
    }>("/api/evaluate", {
      method: "POST",
      body: JSON.stringify({ recommended_job_ids, relevant_job_ids, k }),
    }),
};

// Export api object for convenience
export const api = {
  auth,
  resumes,
  jobs,
  applications,
  recommendations,
  dashboard,
  evaluation,
};
