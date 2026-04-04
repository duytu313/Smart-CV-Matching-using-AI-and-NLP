"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, Job } from "@/lib/api"; // Đã thêm Job vào import
import { ArrowLeft, X, Plus, Sparkles, AlertCircle } from "lucide-react";
import Link from "next/link";

export default function NewJobPage() {
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [skillInput, setSkillInput] = useState("");
  const [formData, setFormData] = useState({
    title: "",
    company: "",
    location: "",
    job_type: "full-time",
    experience_min: "",
    experience_max: "",
    salary_min: "",
    salary_max: "",
    description: "",
    requirements: "",
    required_skills: [] as string[],
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  function addSkill() {
    const skill = skillInput.trim();
    if (skill && !formData.required_skills.includes(skill)) {
      setFormData({
        ...formData,
        required_skills: [...formData.required_skills, skill],
      });
      setSkillInput("");
    }
  }

  function removeSkill(skill: string) {
    setFormData({
      ...formData,
      required_skills: formData.required_skills.filter((s) => s !== skill),
    });
  }

  function validate(): boolean {
    const newErrors: Record<string, string> = {};
    if (!formData.title.trim()) newErrors.title = "Job title is required";
    if (!formData.company.trim())
      newErrors.company = "Company name is required";
    if (!formData.description.trim())
      newErrors.description = "Description is required";
    if (formData.required_skills.length === 0) {
      newErrors.required_skills = "Add at least one required skill";
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validate()) return;

    setIsSubmitting(true);
    setErrors({});

    try {
      // Chuẩn bị payload với đúng types
      const payload: Partial<Job> = {
        title: formData.title,
        company: formData.company,
        location: formData.location || undefined,
        job_type: formData.job_type,
        salary_min: formData.salary_min
          ? parseInt(formData.salary_min)
          : undefined,
        salary_max: formData.salary_max
          ? parseInt(formData.salary_max)
          : undefined,
        description: formData.description,
        requirements: formData.requirements || undefined,
        required_skills: formData.required_skills,
        preferred_skills: [],
        experience_min: formData.experience_min
          ? parseInt(formData.experience_min)
          : undefined,
        experience_max: formData.experience_max
          ? parseInt(formData.experience_max)
          : undefined,
        is_active: true,
      };

      console.log("Creating job with payload:", payload);

      const response = await api.jobs.create(payload);
      console.log("Job created successfully:", response);

      // Chuyển hướng về trang jobs
      router.push("/recruiter/jobs");
      router.refresh();
    } catch (error: any) {
      console.error("Failed to create job:", error);

      let errorMessage = "Failed to create job posting. Please try again.";
      if (error.message) {
        errorMessage = error.message;
      }
      if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      }

      setErrors({ submit: errorMessage });
      window.scrollTo({ top: 0, behavior: "smooth" });
    } finally {
      setIsSubmitting(false);
    }
  }

  const jobTypes = [
    { value: "full-time", label: "Full-time" },
    { value: "part-time", label: "Part-time" },
    { value: "contract", label: "Contract" },
    { value: "internship", label: "Internship" },
    { value: "remote", label: "Remote" },
  ];

  return (
    <div className="max-w-3xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-4 mb-8">
        <Link
          href="/recruiter/jobs"
          className="p-2 hover:bg-muted rounded-lg transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold">Post a New Job</h1>
          <p className="text-muted-foreground mt-1">
            Fill in the details to create a new job listing
          </p>
        </div>
      </div>

      {/* Error Display */}
      {errors.submit && (
        <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-red-600 text-sm font-medium">
              Error creating job
            </p>
            <p className="text-red-500 text-sm mt-1">{errors.submit}</p>
          </div>
          <button
            onClick={() => setErrors({})}
            className="text-red-500 hover:text-red-700"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-8">
        {/* Basic Information */}
        <div className="bg-card rounded-xl border border-border p-6 space-y-6">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-primary" />
            Basic Information
          </h2>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">
                Job Title <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={formData.title}
                onChange={(e) =>
                  setFormData({ ...formData, title: e.target.value })
                }
                placeholder="e.g. Senior Software Engineer"
                className={`w-full px-4 py-2 border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/20 ${
                  errors.title ? "border-red-500" : "border-border"
                }`}
              />
              {errors.title && (
                <p className="text-sm text-red-500 mt-1">{errors.title}</p>
              )}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">
                  Company <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={formData.company}
                  onChange={(e) =>
                    setFormData({ ...formData, company: e.target.value })
                  }
                  placeholder="e.g. Acme Inc."
                  className={`w-full px-4 py-2 border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/20 ${
                    errors.company ? "border-red-500" : "border-border"
                  }`}
                />
                {errors.company && (
                  <p className="text-sm text-red-500 mt-1">{errors.company}</p>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">
                  Location
                </label>
                <input
                  type="text"
                  value={formData.location}
                  onChange={(e) =>
                    setFormData({ ...formData, location: e.target.value })
                  }
                  placeholder="e.g. San Francisco, CA or Remote"
                  className="w-full px-4 py-2 border border-border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">
                  Job Type
                </label>
                <select
                  value={formData.job_type}
                  onChange={(e) =>
                    setFormData({ ...formData, job_type: e.target.value })
                  }
                  className="w-full px-4 py-2 border border-border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
                >
                  {jobTypes.map((type) => (
                    <option key={type.value} value={type.value}>
                      {type.label}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">
                  Experience Range (years)
                </label>
                <div className="flex gap-2">
                  <input
                    type="number"
                    value={formData.experience_min}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        experience_min: e.target.value,
                      })
                    }
                    placeholder="Min"
                    className="flex-1 px-4 py-2 border border-border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
                  />
                  <span className="text-muted-foreground self-center">to</span>
                  <input
                    type="number"
                    value={formData.experience_max}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        experience_max: e.target.value,
                      })
                    }
                    placeholder="Max"
                    className="flex-1 px-4 py-2 border border-border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
                  />
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">
                  Salary Min (USD)
                </label>
                <input
                  type="number"
                  value={formData.salary_min}
                  onChange={(e) =>
                    setFormData({ ...formData, salary_min: e.target.value })
                  }
                  placeholder="e.g. 80000"
                  className="w-full px-4 py-2 border border-border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">
                  Salary Max (USD)
                </label>
                <input
                  type="number"
                  value={formData.salary_max}
                  onChange={(e) =>
                    setFormData({ ...formData, salary_max: e.target.value })
                  }
                  placeholder="e.g. 120000"
                  className="w-full px-4 py-2 border border-border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Required Skills */}
        <div className="bg-card rounded-xl border border-border p-6 space-y-4">
          <h2 className="text-lg font-semibold">
            Required Skills <span className="text-red-500">*</span>
          </h2>
          <p className="text-sm text-muted-foreground">
            Add the key skills required for this position. These will be used
            for AI-powered candidate matching.
          </p>

          <div className="flex gap-2">
            <input
              type="text"
              value={skillInput}
              onChange={(e) => setSkillInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  addSkill();
                }
              }}
              placeholder="Type a skill and press Enter"
              className="flex-1 px-4 py-2 border border-border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
            />
            <button
              type="button"
              onClick={addSkill}
              className="px-4 py-2 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 transition-colors"
            >
              <Plus className="w-5 h-5" />
            </button>
          </div>

          {formData.required_skills.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {formData.required_skills.map((skill) => (
                <span
                  key={skill}
                  className="inline-flex items-center gap-1 px-3 py-1 bg-primary/10 text-primary rounded-full text-sm"
                >
                  {skill}
                  <button
                    type="button"
                    onClick={() => removeSkill(skill)}
                    className="p-0.5 hover:bg-primary/20 rounded-full"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
            </div>
          )}
          {errors.required_skills && (
            <p className="text-sm text-red-500">{errors.required_skills}</p>
          )}
        </div>

        {/* Description */}
        <div className="bg-card rounded-xl border border-border p-6 space-y-4">
          <h2 className="text-lg font-semibold">Job Description</h2>

          <div>
            <label className="block text-sm font-medium mb-2">
              Description <span className="text-red-500">*</span>
            </label>
            <textarea
              value={formData.description}
              onChange={(e) =>
                setFormData({ ...formData, description: e.target.value })
              }
              rows={6}
              placeholder="Describe the role, responsibilities, and what makes this opportunity exciting..."
              className={`w-full px-4 py-2 border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/20 resize-none ${
                errors.description ? "border-red-500" : "border-border"
              }`}
            />
            {errors.description && (
              <p className="text-sm text-red-500 mt-1">{errors.description}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">
              Requirements
            </label>
            <textarea
              value={formData.requirements}
              onChange={(e) =>
                setFormData({ ...formData, requirements: e.target.value })
              }
              rows={4}
              placeholder="List the qualifications and requirements for this role..."
              className="w-full px-4 py-2 border border-border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/20 resize-none"
            />
          </div>
        </div>

        {/* Submit */}
        <div className="flex items-center justify-end gap-4">
          <Link
            href="/recruiter/jobs"
            className="px-6 py-2 border border-border rounded-lg font-medium hover:bg-muted transition-colors"
          >
            Cancel
          </Link>
          <button
            type="submit"
            disabled={isSubmitting}
            className="px-6 py-2 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSubmitting ? "Posting..." : "Post Job"}
          </button>
        </div>
      </form>
    </div>
  );
}
