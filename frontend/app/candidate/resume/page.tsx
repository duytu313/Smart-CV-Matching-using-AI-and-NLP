"use client";

import { useEffect, useState, useCallback } from "react";
import { resumes, Resume } from "@/lib/api";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Upload,
  FileText,
  CheckCircle,
  Plus,
  Sparkles,
  Clock,
  Briefcase,
  GraduationCap,
  Star,
  Loader2,
  Image as ImageIcon,
  Trash2,
  AlertTriangle,
} from "lucide-react";
import { toast } from "sonner";

// Interface cho API response
interface AnalysisResult {
  skills: string[];
  skills_by_category: Record<string, string[]>;
  experience_years?: number;
  education: { degree: string; institution: string; year: string }[];
  contact_info: Record<string, string>;
  skill_suggestions: string[];
}

// Hàm lưu primary resume ID vào localStorage
const savePrimaryResumeId = (id: number) => {
  localStorage.setItem("primary_resume_id", id.toString());
  // Dispatch event để các tab khác cập nhật
  window.dispatchEvent(new Event("primaryResumeChanged"));
};

// Hàm lấy primary resume ID từ localStorage
const getPrimaryResumeId = (): number | null => {
  const id = localStorage.getItem("primary_resume_id");
  return id ? parseInt(id) : null;
};

// Hàm kiểm tra file type
const isImageFile = (file: File): boolean => {
  const imageExtensions = [
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
    ".tiff",
    ".tif",
    ".webp",
  ];
  const fileExt = "." + file.name.split(".").pop()?.toLowerCase();
  return imageExtensions.includes(fileExt);
};

const isDocumentFile = (file: File): boolean => {
  const docExtensions = [".pdf", ".docx", ".txt"];
  const fileExt = "." + file.name.split(".").pop()?.toLowerCase();
  return docExtensions.includes(fileExt);
};

const getFileIcon = (file: File) => {
  if (isImageFile(file))
    return <ImageIcon className="h-10 w-10 text-primary" />;
  return <FileText className="h-10 w-10 text-primary" />;
};

export default function ResumePage() {
  const [resumeList, setResumeList] = useState<Resume[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [analyzeDialogOpen, setAnalyzeDialogOpen] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [resumeTitle, setResumeTitle] = useState("");
  const [pasteText, setPasteText] = useState("");
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(
    null,
  );
  const [settingPrimary, setSettingPrimary] = useState<number | null>(null);
  const [deletingResume, setDeletingResume] = useState<number | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [resumeToDelete, setResumeToDelete] = useState<Resume | null>(null);

  useEffect(() => {
    loadResumes();

    // Lắng nghe sự kiện thay đổi primary resume từ các tab khác
    const handlePrimaryChange = () => {
      loadResumes();
    };

    window.addEventListener("primaryResumeChanged", handlePrimaryChange);
    return () => {
      window.removeEventListener("primaryResumeChanged", handlePrimaryChange);
    };
  }, []);

  const loadResumes = async () => {
    try {
      const data = await resumes.list();
      setResumeList(data);

      // Đảm bảo UI hiển thị đúng primary resume dựa trên localStorage
      const savedPrimaryId = getPrimaryResumeId();
      if (savedPrimaryId) {
        const hasPrimary = data.some(
          (r) => r.id === savedPrimaryId && r.is_primary,
        );
        if (!hasPrimary && data.length > 0) {
          // Nếu không có primary trong data, set cái đầu tiên làm primary
          const firstResume = data[0];
          if (firstResume) {
            await handleSetPrimary(firstResume.id, false);
          }
        }
      }
    } catch (error) {
      console.log("Could not load resumes:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleSetPrimary = async (
    resumeId: number,
    showToast: boolean = true,
  ) => {
    setSettingPrimary(resumeId);
    try {
      // Gọi API set primary (đã được sửa trong api.ts)
      await resumes.setPrimary(resumeId);

      // Cập nhật UI ngay lập tức
      const updatedResumes = resumeList.map((r) => ({
        ...r,
        is_primary: r.id === resumeId,
      }));
      setResumeList(updatedResumes);

      // Lưu vào localStorage
      savePrimaryResumeId(resumeId);

      if (showToast) {
        toast.success("Primary resume updated successfully!");
      }
    } catch (error) {
      console.error("Failed to set primary resume:", error);

      // Nếu API thất bại, thử cập nhật lại danh sách để đồng bộ
      try {
        const freshData = await resumes.list();
        setResumeList(freshData);
      } catch (refreshError) {
        console.error("Failed to refresh resume list:", refreshError);
      }

      if (showToast) {
        toast.error(
          error instanceof Error
            ? error.message
            : "Failed to update primary resume. Please try again.",
        );
      }
    } finally {
      setSettingPrimary(null);
    }
  };

  // Hàm xóa resume
  const handleDeleteResume = async () => {
    if (!resumeToDelete) return;

    setDeletingResume(resumeToDelete.id);
    try {
      await resumes.delete(resumeToDelete.id);
      toast.success("Resume deleted successfully!");

      // Reload resumes
      await loadResumes();

      // Close dialog
      setDeleteDialogOpen(false);
      setResumeToDelete(null);
    } catch (error) {
      console.error("Failed to delete resume:", error);
      toast.error(
        error instanceof Error
          ? error.message
          : "Failed to delete resume. Please try again.",
      );
    } finally {
      setDeletingResume(null);
    }
  };

  const handleFileUpload = async () => {
    if (!selectedFile || !resumeTitle) {
      toast.error("Please select a file and enter a title");
      return;
    }

    setUploading(true);
    try {
      await resumes.upload(selectedFile, resumeTitle);
      toast.success("Resume uploaded successfully!");
      setUploadDialogOpen(false);
      setSelectedFile(null);
      setResumeTitle("");
      await loadResumes();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const handleAnalyze = async () => {
    if (!pasteText.trim()) {
      toast.error("Please paste your resume text");
      return;
    }

    setAnalyzing(true);
    try {
      const result = await resumes.analyze(pasteText);
      setAnalysisResult(result);
      toast.success("Analysis complete!");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Analysis failed");
    } finally {
      setAnalyzing(false);
    }
  };

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      const file = e.dataTransfer.files[0];

      const allowedExtensions = [
        ".pdf",
        ".docx",
        ".txt",
        ".png",
        ".jpg",
        ".jpeg",
        ".bmp",
        ".tiff",
        ".tif",
        ".webp",
      ];
      const fileExt = "." + file.name.split(".").pop()?.toLowerCase();

      if (file && allowedExtensions.includes(fileExt)) {
        setSelectedFile(file);
        if (!resumeTitle) {
          setResumeTitle(file.name.replace(/\.[^/.]+$/, ""));
        }
      } else {
        toast.error(
          "Please upload a PDF, DOCX, TXT, or image file (PNG, JPG, JPEG, BMP, TIFF, WEBP)",
        );
      }
    },
    [resumeTitle],
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
  }, []);

  // Lấy danh sách các định dạng file được hỗ trợ để hiển thị
  const getAcceptedFileTypes = () => {
    return ".pdf,.docx,.txt,.png,.jpg,.jpeg,.bmp,.tiff,.tif,.webp";
  };

  const getSupportedFormatsText = () => {
    return "PDF, DOCX, TXT, PNG, JPG, JPEG, BMP, TIFF, WEBP";
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-3xl font-bold">My Resumes</h1>
          <p className="text-muted-foreground mt-1">
            Manage your resumes and analyze your skills
          </p>
        </div>
        <div className="flex gap-3">
          <Dialog open={analyzeDialogOpen} onOpenChange={setAnalyzeDialogOpen}>
            <DialogTrigger asChild>
              <Button variant="outline" className="gap-2">
                <Sparkles className="h-4 w-4" />
                Analyze Text
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle>Analyze Resume Text</DialogTitle>
                <DialogDescription>
                  Paste your resume text to extract skills and insights
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4">
                <div>
                  <Label htmlFor="resume-text">Resume Text</Label>
                  <Textarea
                    id="resume-text"
                    placeholder="Paste your resume content here..."
                    className="mt-2 h-48"
                    value={pasteText}
                    onChange={(e) => setPasteText(e.target.value)}
                  />
                </div>
                <Button
                  onClick={handleAnalyze}
                  disabled={analyzing || !pasteText.trim()}
                  className="w-full gap-2"
                >
                  {analyzing ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Analyzing...
                    </>
                  ) : (
                    <>
                      <Sparkles className="h-4 w-4" />
                      Analyze Resume
                    </>
                  )}
                </Button>

                {analysisResult && (
                  <div className="space-y-4 border-t pt-4">
                    <div>
                      <h4 className="font-semibold mb-2 flex items-center gap-2">
                        <CheckCircle className="h-4 w-4 text-emerald-600" />
                        Extracted Skills ({analysisResult.skills.length})
                      </h4>
                      <div className="flex flex-wrap gap-2">
                        {analysisResult.skills.map((skill) => (
                          <Badge key={skill} variant="secondary">
                            {skill}
                          </Badge>
                        ))}
                      </div>
                    </div>

                    {analysisResult.experience_years && (
                      <div>
                        <h4 className="font-semibold mb-2 flex items-center gap-2">
                          <Clock className="h-4 w-4 text-primary" />
                          Experience
                        </h4>
                        <p className="text-muted-foreground">
                          ~{analysisResult.experience_years} years
                        </p>
                      </div>
                    )}

                    {analysisResult.education.length > 0 && (
                      <div>
                        <h4 className="font-semibold mb-2 flex items-center gap-2">
                          <GraduationCap className="h-4 w-4 text-primary" />
                          Education
                        </h4>
                        <ul className="space-y-1 text-sm text-muted-foreground">
                          {analysisResult.education.map((edu, i) => (
                            <li key={i}>
                              {edu.degree} - {edu.institution} ({edu.year})
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {analysisResult.skill_suggestions.length > 0 && (
                      <div>
                        <h4 className="font-semibold mb-2 flex items-center gap-2">
                          <Star className="h-4 w-4 text-amber-600" />
                          Suggested Skills to Add
                        </h4>
                        <div className="flex flex-wrap gap-2">
                          {analysisResult.skill_suggestions.map((skill) => (
                            <Badge key={skill} variant="outline">
                              {skill}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </DialogContent>
          </Dialog>

          <Dialog open={uploadDialogOpen} onOpenChange={setUploadDialogOpen}>
            <DialogTrigger asChild>
              <Button className="gap-2">
                <Plus className="h-4 w-4" />
                Upload Resume
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Upload Resume</DialogTitle>
                <DialogDescription>
                  Upload your CV in {getSupportedFormatsText()} format
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4">
                <div>
                  <Label htmlFor="title">Resume Title</Label>
                  <Input
                    id="title"
                    placeholder="e.g., Software Engineer Resume 2024"
                    value={resumeTitle}
                    onChange={(e) => setResumeTitle(e.target.value)}
                    className="mt-2"
                  />
                </div>

                <div
                  onDrop={handleDrop}
                  onDragOver={handleDragOver}
                  className="border-2 border-dashed border-border rounded-lg p-8 text-center hover:border-primary/50 transition-colors cursor-pointer"
                  onClick={() => document.getElementById("file-input")?.click()}
                >
                  <input
                    id="file-input"
                    type="file"
                    accept={getAcceptedFileTypes()}
                    className="hidden"
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) {
                        setSelectedFile(file);
                        if (!resumeTitle) {
                          setResumeTitle(file.name.replace(/\.[^/.]+$/, ""));
                        }
                      }
                    }}
                  />
                  {selectedFile ? (
                    <div className="flex flex-col items-center gap-2">
                      {getFileIcon(selectedFile)}
                      <p className="font-medium">{selectedFile.name}</p>
                      <p className="text-sm text-muted-foreground">
                        {isImageFile(selectedFile)
                          ? "Image file - Text will be extracted using OCR"
                          : "Document file"}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        Click or drop to replace
                      </p>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center gap-2">
                      <Upload className="h-10 w-10 text-muted-foreground" />
                      <p className="font-medium">Drop your resume here</p>
                      <p className="text-sm text-muted-foreground">
                        or click to browse ({getSupportedFormatsText()})
                      </p>
                      <p className="text-xs text-muted-foreground mt-2">
                        💡 Image files (PNG, JPG, etc.) will be processed using
                        OCR
                      </p>
                    </div>
                  )}
                </div>

                <Button
                  onClick={handleFileUpload}
                  disabled={uploading || !selectedFile || !resumeTitle}
                  className="w-full"
                >
                  {uploading ? "Uploading..." : "Upload Resume"}
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-600">
              <AlertTriangle className="h-5 w-5" />
              Delete Resume
            </DialogTitle>
            <DialogDescription>
              Are you sure you want to delete "{resumeToDelete?.title}"?
              {resumeToDelete?.is_primary && (
                <span className="block mt-2 text-amber-600">
                  ⚠️ This is your primary resume. Another resume will be set as
                  primary after deletion.
                </span>
              )}
              This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2">
            <Button
              variant="outline"
              onClick={() => {
                setDeleteDialogOpen(false);
                setResumeToDelete(null);
              }}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDeleteResume}
              disabled={deletingResume === resumeToDelete?.id}
            >
              {deletingResume === resumeToDelete?.id ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  Deleting...
                </>
              ) : (
                <>
                  <Trash2 className="h-4 w-4 mr-2" />
                  Delete Resume
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Resume List */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      ) : resumeList.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-12">
            <FileText className="h-12 w-12 text-muted-foreground/50 mb-4" />
            <h3 className="text-lg font-semibold mb-2">No resumes yet</h3>
            <p className="text-muted-foreground text-center max-w-sm mb-4">
              Upload your first resume to get AI-powered job recommendations
            </p>
            <Button onClick={() => setUploadDialogOpen(true)} className="gap-2">
              <Plus className="h-4 w-4" />
              Upload Your First Resume
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {resumeList.map((resume) => (
            <Card
              key={resume.id}
              className={resume.is_primary ? "ring-2 ring-primary" : ""}
            >
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="flex items-center gap-2">
                      <FileText className="h-5 w-5 flex-shrink-0" />
                      <span className="break-words">{resume.title}</span>
                    </CardTitle>
                    <CardDescription>
                      Uploaded{" "}
                      {new Date(resume.created_at).toLocaleDateString()}
                    </CardDescription>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0 ml-2">
                    {resume.is_primary ? (
                      <Badge className="gap-1 bg-primary">
                        <Star className="h-3 w-3 fill-current" />
                        Primary
                      </Badge>
                    ) : (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleSetPrimary(resume.id)}
                        disabled={settingPrimary === resume.id}
                        className="gap-1"
                      >
                        {settingPrimary === resume.id ? (
                          <Loader2 className="h-3 w-3 animate-spin" />
                        ) : (
                          <Star className="h-3 w-3" />
                        )}
                        Set as Primary
                      </Button>
                    )}
                    {/* Nút xóa */}
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        setResumeToDelete(resume);
                        setDeleteDialogOpen(true);
                      }}
                      className="text-red-600 hover:text-red-700 hover:bg-red-50"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {resume.experience_years && resume.experience_years > 0 && (
                    <div className="flex items-center gap-2 text-sm">
                      <Briefcase className="h-4 w-4 text-muted-foreground" />
                      <span>{resume.experience_years} years experience</span>
                    </div>
                  )}

                  {resume.skills && resume.skills.length > 0 && (
                    <div>
                      <p className="text-sm text-muted-foreground mb-2">
                        Skills
                      </p>
                      <div className="flex flex-wrap gap-1.5">
                        {resume.skills.slice(0, 8).map((skill) => (
                          <Badge
                            key={skill}
                            variant="secondary"
                            className="text-xs"
                          >
                            {skill}
                          </Badge>
                        ))}
                        {resume.skills.length > 8 && (
                          <Badge variant="outline" className="text-xs">
                            +{resume.skills.length - 8} more
                          </Badge>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Hiển thị thông báo nếu không có skills */}
                  {(!resume.skills || resume.skills.length === 0) && (
                    <p className="text-sm text-muted-foreground italic">
                      No skills extracted yet. Upload a new version or edit
                      manually.
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
