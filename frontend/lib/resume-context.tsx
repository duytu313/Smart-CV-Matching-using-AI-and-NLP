// lib/resume-context.tsx
"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
} from "react";
import { resumes, Resume } from "./api";

interface ResumeContextType {
  resumes: Resume[];
  primaryResume: Resume | null;
  loading: boolean;
  refreshResumes: () => Promise<void>;
  setPrimaryResume: (resumeId: number) => Promise<void>;
}

const ResumeContext = createContext<ResumeContextType | undefined>(undefined);

export function ResumeProvider({ children }: { children: ReactNode }) {
  const [resumesList, setResumesList] = useState<Resume[]>([]);
  const [primaryResume, setPrimaryResumeState] = useState<Resume | null>(null);
  const [loading, setLoading] = useState(true);

  const loadResumes = async () => {
    try {
      setLoading(true);
      const data = await resumes.list();
      setResumesList(data);
      const primary = data.find((r) => r.is_primary) || null;
      setPrimaryResumeState(primary);

      // Lưu vào localStorage để các trang khác có thể đọc
      if (primary) {
        localStorage.setItem("primary_resume_id", primary.id.toString());
        localStorage.setItem("primary_resume", JSON.stringify(primary));
      }
    } catch (error) {
      console.error("Failed to load resumes:", error);
    } finally {
      setLoading(false);
    }
  };

  const setPrimaryResume = async (resumeId: number) => {
    try {
      await resumes.setPrimary(resumeId);
      await loadResumes(); // Reload after setting
      return Promise.resolve();
    } catch (error) {
      console.error("Failed to set primary resume:", error);
      throw error;
    }
  };

  useEffect(() => {
    loadResumes();
  }, []);

  return (
    <ResumeContext.Provider
      value={{
        resumes: resumesList,
        primaryResume,
        loading,
        refreshResumes: loadResumes,
        setPrimaryResume,
      }}
    >
      {children}
    </ResumeContext.Provider>
  );
}

export function useResume() {
  const context = useContext(ResumeContext);
  if (context === undefined) {
    throw new Error("useResume must be used within a ResumeProvider");
  }
  return context;
}
