"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api, User } from "@/lib/api";
import {
  User as UserIcon,
  Mail,
  Phone,
  MapPin,
  Save,
  AlertCircle,
  Briefcase,
  LogOut,
} from "lucide-react";

export default function CandidateSettingsPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);
  const [formData, setFormData] = useState({
    full_name: "",
    email: "",
    phone: "",
    location: "",
    bio: "",
    preferred_job_type: "",
    preferred_location: "",
    experience_level: "",
  });

  useEffect(() => {
    loadUserProfile();
  }, []);

  async function loadUserProfile() {
    try {
      setIsLoading(true);
      const currentUser = await api.auth.me();
      setUser(currentUser);
      setFormData({
        full_name: currentUser.full_name || "",
        email: currentUser.email || "",
        phone: "",
        location: "",
        bio: "",
        preferred_job_type: "",
        preferred_location: "",
        experience_level: "",
      });
    } catch (error) {
      console.error("Failed to load user:", error);
      setMessage({ type: "error", text: "Failed to load profile" });
    } finally {
      setIsLoading(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setIsSubmitting(true);
    setMessage(null);

    try {
      // Note: API hiện tại không có endpoint update profile
      // Bạn cần thêm endpoint này trong backend
      // Tạm thời chỉ hiển thị thông báo
      setMessage({
        type: "success",
        text: "Profile updated successfully! (Demo - API endpoint not implemented yet)",
      });

      // Khi có backend endpoint, sử dụng:
      // const response = await api.auth.updateProfile(formData);
      // setUser(response);
    } catch (error) {
      console.error("Failed to update profile:", error);
      setMessage({
        type: "error",
        text: "Failed to update profile. Please try again.",
      });
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleLogout() {
    localStorage.removeItem("auth_token");
    router.push("/auth/login");
  }

  if (isLoading) {
    return (
      <div className="max-w-2xl mx-auto space-y-8">
        <div className="animate-pulse">
          <div className="h-8 w-32 bg-muted rounded mb-2"></div>
          <div className="h-4 w-48 bg-muted rounded"></div>
        </div>
        <div className="bg-card rounded-xl border border-border p-6 space-y-6">
          <div className="h-6 w-32 bg-muted rounded"></div>
          <div className="space-y-4">
            <div className="h-10 bg-muted rounded"></div>
            <div className="h-10 bg-muted rounded"></div>
            <div className="h-24 bg-muted rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto space-y-8">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">Settings</h1>
          <p className="text-muted-foreground mt-1">
            Manage your account settings
          </p>
        </div>
        <button
          onClick={handleLogout}
          className="flex items-center gap-2 px-4 py-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
        >
          <LogOut className="w-4 h-4" />
          Logout
        </button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Profile Section */}
        <div className="bg-card rounded-xl border border-border p-6 space-y-6">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <UserIcon className="w-5 h-5 text-primary" />
            Profile Information
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
              <label className="block text-sm font-medium mb-2">
                Full Name
              </label>
              <input
                type="text"
                value={formData.full_name}
                onChange={(e) =>
                  setFormData({ ...formData, full_name: e.target.value })
                }
                className="w-full px-4 py-2 border border-border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2">Email</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) =>
                    setFormData({ ...formData, email: e.target.value })
                  }
                  className="w-full pl-10 pr-4 py-2 border border-border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Phone</label>
              <div className="relative">
                <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <input
                  type="tel"
                  value={formData.phone}
                  onChange={(e) =>
                    setFormData({ ...formData, phone: e.target.value })
                  }
                  placeholder="+1 234 567 8900"
                  className="w-full pl-10 pr-4 py-2 border border-border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
                />
              </div>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Location</label>
            <div className="relative">
              <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <input
                type="text"
                value={formData.location}
                onChange={(e) =>
                  setFormData({ ...formData, location: e.target.value })
                }
                placeholder="City, State or Country"
                className="w-full pl-10 pr-4 py-2 border border-border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">
              Professional Summary
            </label>
            <textarea
              value={formData.bio}
              onChange={(e) =>
                setFormData({ ...formData, bio: e.target.value })
              }
              rows={4}
              placeholder="Write a brief summary about yourself, your experience, and career goals..."
              className="w-full px-4 py-2 border border-border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/20 resize-none"
            />
          </div>
        </div>

        {/* Job Preferences */}
        <div className="bg-card rounded-xl border border-border p-6 space-y-6">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Briefcase className="w-5 h-5 text-primary" />
            Job Preferences
          </h2>
          <p className="text-sm text-muted-foreground">
            These preferences help our AI provide better job recommendations.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2">
                Preferred Job Type
              </label>
              <select
                value={formData.preferred_job_type}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    preferred_job_type: e.target.value,
                  })
                }
                className="w-full px-4 py-2 border border-border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
              >
                <option value="">Any</option>
                <option value="full-time">Full-time</option>
                <option value="part-time">Part-time</option>
                <option value="contract">Contract</option>
                <option value="internship">Internship</option>
                <option value="remote">Remote</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">
                Experience Level
              </label>
              <select
                value={formData.experience_level}
                onChange={(e) =>
                  setFormData({ ...formData, experience_level: e.target.value })
                }
                className="w-full px-4 py-2 border border-border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
              >
                <option value="">Any</option>
                <option value="entry">Entry Level (0-2 years)</option>
                <option value="mid">Mid Level (2-5 years)</option>
                <option value="senior">Senior Level (5-8 years)</option>
                <option value="lead">Lead / Manager (8+ years)</option>
                <option value="executive">Executive (10+ years)</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">
              Preferred Locations
            </label>
            <input
              type="text"
              value={formData.preferred_location}
              onChange={(e) =>
                setFormData({ ...formData, preferred_location: e.target.value })
              }
              placeholder="e.g. San Francisco, New York, Remote"
              className="w-full px-4 py-2 border border-border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
            />
            <p className="text-xs text-muted-foreground mt-1">
              Separate multiple locations with commas
            </p>
          </div>
        </div>

        {/* Message */}
        {message && (
          <div
            className={`flex items-center gap-2 p-4 rounded-lg ${
              message.type === "success"
                ? "bg-emerald-500/10 text-emerald-600 border border-emerald-500/20"
                : "bg-red-500/10 text-red-600 border border-red-500/20"
            }`}
          >
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <span className="text-sm">{message.text}</span>
          </div>
        )}

        {/* Submit */}
        <div className="flex justify-end">
          <button
            type="submit"
            disabled={isSubmitting}
            className="flex items-center gap-2 px-6 py-2 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            {isSubmitting ? "Saving..." : "Save Changes"}
          </button>
        </div>
      </form>

      {/* Note about missing API */}
      <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
        <p className="text-sm text-amber-800">
          <strong>Note:</strong> The profile update API endpoint is not yet
          implemented in the backend. This is a demo interface. When the backend
          is ready, you can add the updateProfile method to the auth API.
        </p>
      </div>
    </div>
  );
}
