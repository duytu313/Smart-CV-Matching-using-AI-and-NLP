"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { jobs, recommendations, Job, JobMatch, resumes, Resume } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { 
  Search, MapPin, Building, Clock, DollarSign, 
  Sparkles, ArrowRight, Briefcase, Filter
} from "lucide-react";
import { toast } from "sonner";

export default function JobsPage() {
  const [jobList, setJobList] = useState<Job[]>([]);
  const [recommendedJobs, setRecommendedJobs] = useState<JobMatch[]>([]);
  const [resumeSkills, setResumeSkills] = useState<string[]>([]);
  const [userResumes, setUserResumes] = useState<Resume[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingRecs, setLoadingRecs] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [locationFilter, setLocationFilter] = useState("");
  const [jobTypeFilter, setJobTypeFilter] = useState<string>("");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [activeTab, setActiveTab] = useState("recommended");

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    if (activeTab === "all") {
      loadJobs();
    }
  }, [page, searchQuery, locationFilter, jobTypeFilter, activeTab]);

  const loadData = async () => {
    try {
      // Load user's resumes
      const resumeData = await resumes.list();
      setUserResumes(resumeData);

      // Get primary resume for recommendations
      const primaryResume = resumeData.find(r => r.is_primary) || resumeData[0];
      
      if (primaryResume?.raw_text) {
        const recsResult = await recommendations.getRecommendations({
          resume_id: primaryResume.id,
          k: 20,
          min_score: 20,
        });
        setRecommendedJobs(recsResult.recommendations);
        setResumeSkills(recsResult.resume_skills);
      }
    } catch (error) {
      console.log("Could not load recommendations:", error);
    } finally {
      setLoadingRecs(false);
    }
  };

  const loadJobs = async () => {
    setLoading(true);
    try {
      const result = await jobs.list({
        page,
        page_size: 20,
        search: searchQuery || undefined,
        location: locationFilter || undefined,
        job_type: jobTypeFilter || undefined,
      });
      setJobList(result.jobs);
      setTotalPages(result.total_pages);
    } catch (error) {
      console.log("Could not load jobs:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadJobs();
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return "text-chart-2";
    if (score >= 60) return "text-primary";
    if (score >= 40) return "text-chart-3";
    return "text-muted-foreground";
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Browse Jobs</h1>
        <p className="text-muted-foreground mt-1">
          Find opportunities that match your skills
        </p>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="recommended" className="gap-2">
            <Sparkles className="h-4 w-4" />
            AI Recommended
          </TabsTrigger>
          <TabsTrigger value="all" className="gap-2">
            <Briefcase className="h-4 w-4" />
            All Jobs
          </TabsTrigger>
        </TabsList>

        {/* Recommended Jobs Tab */}
        <TabsContent value="recommended" className="mt-6">
          {loadingRecs ? (
            <div className="flex items-center justify-center py-12">
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
            </div>
          ) : recommendedJobs.length === 0 ? (
            <Card className="border-dashed">
              <CardContent className="flex flex-col items-center justify-center py-12">
                <Sparkles className="h-12 w-12 text-muted-foreground/50 mb-4" />
                <h3 className="text-lg font-semibold mb-2">No recommendations yet</h3>
                <p className="text-muted-foreground text-center max-w-sm">
                  Upload a resume to get personalized job recommendations
                </p>
                <Link href="/candidate/resume">
                  <Button className="mt-4">Upload Resume</Button>
                </Link>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-4">
              {resumeSkills.length > 0 && (
                <div className="flex flex-wrap items-center gap-2 text-sm">
                  <span className="text-muted-foreground">Your skills:</span>
                  {resumeSkills.slice(0, 8).map((skill) => (
                    <Badge key={skill} variant="secondary" className="text-xs">
                      {skill}
                    </Badge>
                  ))}
                  {resumeSkills.length > 8 && (
                    <Badge variant="outline" className="text-xs">
                      +{resumeSkills.length - 8} more
                    </Badge>
                  )}
                </div>
              )}

              <div className="grid gap-4">
                {recommendedJobs.map((job) => (
                  <RecommendedJobCard key={job.job_id} job={job} />
                ))}
              </div>
            </div>
          )}
        </TabsContent>

        {/* All Jobs Tab */}
        <TabsContent value="all" className="mt-6 space-y-6">
          {/* Search and Filters */}
          <form onSubmit={handleSearch} className="flex gap-4 flex-wrap">
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search jobs..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
            <div className="relative min-w-[150px]">
              <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Location"
                value={locationFilter}
                onChange={(e) => setLocationFilter(e.target.value)}
                className="pl-10"
              />
            </div>
            <Select value={jobTypeFilter} onValueChange={setJobTypeFilter}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Job Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                <SelectItem value="full-time">Full-time</SelectItem>
                <SelectItem value="part-time">Part-time</SelectItem>
                <SelectItem value="contract">Contract</SelectItem>
                <SelectItem value="remote">Remote</SelectItem>
              </SelectContent>
            </Select>
            <Button type="submit">Search</Button>
          </form>

          {/* Job List */}
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
            </div>
          ) : jobList.length === 0 ? (
            <Card className="border-dashed">
              <CardContent className="flex flex-col items-center justify-center py-12">
                <Briefcase className="h-12 w-12 text-muted-foreground/50 mb-4" />
                <h3 className="text-lg font-semibold mb-2">No jobs found</h3>
                <p className="text-muted-foreground text-center">
                  Try adjusting your search filters
                </p>
              </CardContent>
            </Card>
          ) : (
            <>
              <div className="grid gap-4">
                {jobList.map((job) => (
                  <JobCard key={job.id} job={job} />
                ))}
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex justify-center gap-2">
                  <Button
                    variant="outline"
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={page === 1}
                  >
                    Previous
                  </Button>
                  <span className="flex items-center px-4 text-sm text-muted-foreground">
                    Page {page} of {totalPages}
                  </span>
                  <Button
                    variant="outline"
                    onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                  >
                    Next
                  </Button>
                </div>
              )}
            </>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}

function RecommendedJobCard({ job }: { job: JobMatch }) {
  const getScoreColor = (score: number) => {
    if (score >= 80) return "text-chart-2";
    if (score >= 60) return "text-primary";
    if (score >= 40) return "text-chart-3";
    return "text-muted-foreground";
  };

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardContent className="p-6">
        <div className="flex items-start gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10 text-primary shrink-0">
            <Building className="h-6 w-6" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <h3 className="font-semibold text-lg">{job.title}</h3>
                <p className="text-muted-foreground">{job.company}</p>
                <div className="flex flex-wrap items-center gap-3 mt-2 text-sm text-muted-foreground">
                  {job.location && (
                    <span className="flex items-center gap-1">
                      <MapPin className="h-3.5 w-3.5" />
                      {job.location}
                    </span>
                  )}
                  {job.job_type && (
                    <span className="flex items-center gap-1">
                      <Briefcase className="h-3.5 w-3.5" />
                      {job.job_type}
                    </span>
                  )}
                  {(job.salary_min || job.salary_max) && (
                    <span className="flex items-center gap-1">
                      <DollarSign className="h-3.5 w-3.5" />
                      {job.salary_min && job.salary_max
                        ? `$${job.salary_min.toLocaleString()} - $${job.salary_max.toLocaleString()}`
                        : job.salary_min
                        ? `From $${job.salary_min.toLocaleString()}`
                        : `Up to $${job.salary_max?.toLocaleString()}`}
                    </span>
                  )}
                </div>
              </div>
              <div className="text-right shrink-0">
                <p className={`text-3xl font-bold ${getScoreColor(job.match_score)}`}>
                  {Math.round(job.match_score)}%
                </p>
                <p className="text-xs text-muted-foreground">Match Score</p>
              </div>
            </div>

            <div className="mt-4">
              <Progress value={job.match_score} className="h-2" />
            </div>

            <div className="mt-4 flex flex-wrap gap-2">
              {job.matched_skills.slice(0, 5).map((skill) => (
                <Badge key={skill} variant="secondary" className="bg-chart-2/10 text-chart-2 border-0">
                  {skill}
                </Badge>
              ))}
              {job.missing_skills.slice(0, 3).map((skill) => (
                <Badge key={skill} variant="outline" className="text-muted-foreground">
                  {skill}
                </Badge>
              ))}
            </div>

            <p className="mt-3 text-sm text-muted-foreground">
              {job.recommendation_reason}
            </p>

            <div className="mt-4 flex gap-3">
              <Link href={`/candidate/jobs/${job.job_id}`}>
                <Button className="gap-2">
                  View Details <ArrowRight className="h-4 w-4" />
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function JobCard({ job }: { job: Job }) {
  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardContent className="p-6">
        <div className="flex items-start gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-muted text-muted-foreground shrink-0">
            <Building className="h-6 w-6" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <h3 className="font-semibold text-lg">{job.title}</h3>
                <p className="text-muted-foreground">{job.company}</p>
                <div className="flex flex-wrap items-center gap-3 mt-2 text-sm text-muted-foreground">
                  {job.location && (
                    <span className="flex items-center gap-1">
                      <MapPin className="h-3.5 w-3.5" />
                      {job.location}
                    </span>
                  )}
                  {job.job_type && (
                    <span className="flex items-center gap-1">
                      <Briefcase className="h-3.5 w-3.5" />
                      {job.job_type}
                    </span>
                  )}
                  <span className="flex items-center gap-1">
                    <Clock className="h-3.5 w-3.5" />
                    {new Date(job.created_at).toLocaleDateString()}
                  </span>
                </div>
              </div>
            </div>

            {job.required_skills && job.required_skills.length > 0 && (
              <div className="mt-4 flex flex-wrap gap-2">
                {job.required_skills.slice(0, 6).map((skill) => (
                  <Badge key={skill} variant="secondary">
                    {skill}
                  </Badge>
                ))}
                {job.required_skills.length > 6 && (
                  <Badge variant="outline">
                    +{job.required_skills.length - 6} more
                  </Badge>
                )}
              </div>
            )}

            <div className="mt-4">
              <Link href={`/candidate/jobs/${job.id}`}>
                <Button variant="outline" className="gap-2">
                  View Details <ArrowRight className="h-4 w-4" />
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
