"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { dashboard, CandidateDashboard, JobMatch } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { 
  FileText, Briefcase, Send, Clock, CheckCircle, XCircle,
  TrendingUp, ArrowRight, Sparkles, MapPin, Building
} from "lucide-react";
import { toast } from "sonner";

export default function CandidateDashboardPage() {
  const [data, setData] = useState<CandidateDashboard | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    try {
      const result = await dashboard.candidate();
      setData(result);
    } catch (error) {
      toast.error("Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">Failed to load dashboard data</p>
        <Button onClick={loadDashboard} className="mt-4">Retry</Button>
      </div>
    );
  }

  const getScoreColor = (score: number) => {
    if (score >= 80) return "text-chart-2";
    if (score >= 60) return "text-primary";
    if (score >= 40) return "text-chart-3";
    return "text-muted-foreground";
  };

  const getScoreBg = (score: number) => {
    if (score >= 80) return "bg-chart-2";
    if (score >= 60) return "bg-primary";
    if (score >= 40) return "bg-chart-3";
    return "bg-muted";
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Welcome back, {data.user.full_name.split(" ")[0]}</h1>
        <p className="text-muted-foreground mt-1">
          {"Here's an overview of your job search progress"}
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <FileText className="h-6 w-6" />
              </div>
              <div>
                <p className="text-2xl font-bold">{data.stats.resumes_count}</p>
                <p className="text-sm text-muted-foreground">Resumes</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-chart-2/10 text-chart-2">
                <Send className="h-6 w-6" />
              </div>
              <div>
                <p className="text-2xl font-bold">{data.stats.total_applications}</p>
                <p className="text-sm text-muted-foreground">Applications</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-chart-3/10 text-chart-3">
                <Clock className="h-6 w-6" />
              </div>
              <div>
                <p className="text-2xl font-bold">{data.stats.pending_applications}</p>
                <p className="text-sm text-muted-foreground">Pending</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-accent/10 text-accent">
                <CheckCircle className="h-6 w-6" />
              </div>
              <div>
                <p className="text-2xl font-bold">{data.stats.shortlisted}</p>
                <p className="text-sm text-muted-foreground">Shortlisted</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* AI Recommendations */}
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-primary" />
                AI Job Recommendations
              </CardTitle>
              <CardDescription>
                Personalized job matches based on your resume
              </CardDescription>
            </div>
            <Link href="/candidate/jobs">
              <Button variant="outline" size="sm" className="gap-2">
                View All <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
          </CardHeader>
          <CardContent>
            {data.recommendations.length === 0 ? (
              <div className="text-center py-8">
                <Briefcase className="h-12 w-12 text-muted-foreground/50 mx-auto mb-3" />
                <p className="text-muted-foreground">
                  Upload a resume to get personalized recommendations
                </p>
                <Link href="/candidate/resume">
                  <Button className="mt-4">Upload Resume</Button>
                </Link>
              </div>
            ) : (
              <div className="space-y-4">
                {data.recommendations.slice(0, 3).map((job) => (
                  <JobMatchCard key={job.job_id} match={job} />
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recent Applications */}
        <Card>
          <CardHeader>
            <CardTitle>Recent Applications</CardTitle>
            <CardDescription>Track your application status</CardDescription>
          </CardHeader>
          <CardContent>
            {data.applications.length === 0 ? (
              <div className="text-center py-8">
                <Send className="h-12 w-12 text-muted-foreground/50 mx-auto mb-3" />
                <p className="text-muted-foreground text-sm">
                  No applications yet
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {data.applications.slice(0, 5).map((app) => (
                  <div key={app.id} className="flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <p className="font-medium truncate">{app.job?.title}</p>
                      <p className="text-sm text-muted-foreground truncate">
                        {app.job?.company}
                      </p>
                    </div>
                    <StatusBadge status={app.status} />
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Skills Overview */}
        <Card>
          <CardHeader>
            <CardTitle>Your Skills</CardTitle>
            <CardDescription>Extracted from your primary resume</CardDescription>
          </CardHeader>
          <CardContent>
            {data.resumes.length === 0 ? (
              <div className="text-center py-8">
                <FileText className="h-12 w-12 text-muted-foreground/50 mx-auto mb-3" />
                <p className="text-muted-foreground text-sm">
                  Upload a resume to see your skills
                </p>
              </div>
            ) : (
              <div className="flex flex-wrap gap-2">
                {(data.resumes.find(r => r.is_primary)?.skills || data.resumes[0]?.skills || [])
                  .slice(0, 12)
                  .map((skill) => (
                    <Badge key={skill} variant="secondary">
                      {skill}
                    </Badge>
                  ))}
                {((data.resumes.find(r => r.is_primary)?.skills || data.resumes[0]?.skills || []).length > 12) && (
                  <Badge variant="outline">
                    +{(data.resumes.find(r => r.is_primary)?.skills || data.resumes[0]?.skills || []).length - 12} more
                  </Badge>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function JobMatchCard({ match }: { match: JobMatch }) {
  const getScoreColor = (score: number) => {
    if (score >= 80) return "text-chart-2";
    if (score >= 60) return "text-primary";
    if (score >= 40) return "text-chart-3";
    return "text-muted-foreground";
  };

  return (
    <div className="flex items-start gap-4 p-4 rounded-lg border border-border bg-card hover:bg-muted/30 transition-colors">
      <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10 text-primary shrink-0">
        <Building className="h-6 w-6" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <h4 className="font-semibold truncate">{match.title}</h4>
            <p className="text-sm text-muted-foreground">{match.company}</p>
            {match.location && (
              <p className="text-xs text-muted-foreground flex items-center gap-1 mt-1">
                <MapPin className="h-3 w-3" />
                {match.location}
              </p>
            )}
          </div>
          <div className="text-right shrink-0">
            <p className={`text-2xl font-bold ${getScoreColor(match.match_score)}`}>
              {Math.round(match.match_score)}%
            </p>
            <p className="text-xs text-muted-foreground">Match</p>
          </div>
        </div>
        <div className="mt-3">
          <Progress 
            value={match.match_score} 
            className="h-1.5" 
          />
        </div>
        <div className="mt-3 flex flex-wrap gap-1.5">
          {match.matched_skills.slice(0, 4).map((skill) => (
            <Badge key={skill} variant="secondary" className="text-xs bg-chart-2/10 text-chart-2 border-0">
              {skill}
            </Badge>
          ))}
          {match.missing_skills.slice(0, 2).map((skill) => (
            <Badge key={skill} variant="outline" className="text-xs text-muted-foreground">
              {skill}
            </Badge>
          ))}
        </div>
        <p className="mt-2 text-xs text-muted-foreground line-clamp-1">
          {match.recommendation_reason}
        </p>
      </div>
      <Link href={`/candidate/jobs/${match.job_id}`}>
        <Button size="sm" variant="ghost" className="shrink-0">
          View <ArrowRight className="ml-1 h-4 w-4" />
        </Button>
      </Link>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { variant: "default" | "secondary" | "outline" | "destructive"; icon: typeof Clock }> = {
    pending: { variant: "secondary", icon: Clock },
    reviewed: { variant: "secondary", icon: CheckCircle },
    shortlisted: { variant: "default", icon: TrendingUp },
    rejected: { variant: "destructive", icon: XCircle },
    hired: { variant: "default", icon: CheckCircle },
  };

  const { variant, icon: Icon } = config[status] || config.pending;

  return (
    <Badge variant={variant} className="gap-1 capitalize">
      <Icon className="h-3 w-3" />
      {status}
    </Badge>
  );
}
