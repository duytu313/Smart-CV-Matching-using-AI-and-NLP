"use client";

import { useAuth } from "@/lib/auth-context";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Briefcase, FileText, Sparkles, Target, Users, Zap } from "lucide-react";
import Link from "next/link";

export default function HomePage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && user) {
      router.push(user.role === "recruiter" ? "/recruiter" : "/candidate");
    }
  }, [user, loading, router]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto flex h-16 items-center justify-between px-4">
          <div className="flex items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary">
              <Sparkles className="h-5 w-5 text-primary-foreground" />
            </div>
            <span className="text-xl font-semibold">JobMatch AI</span>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/login">
              <Button variant="ghost">Sign In</Button>
            </Link>
            <Link href="/register">
              <Button>Get Started</Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="py-20 lg:py-32">
        <div className="container mx-auto px-4 text-center">
          <div className="mx-auto max-w-3xl">
            <h1 className="text-4xl font-bold tracking-tight sm:text-5xl lg:text-6xl text-balance">
              Find Your Perfect Job Match with{" "}
              <span className="text-primary">AI-Powered</span> Precision
            </h1>
            <p className="mt-6 text-lg text-muted-foreground leading-relaxed text-pretty">
              Upload your resume and let our advanced AI analyze your skills, experience, 
              and career goals to match you with opportunities that truly fit. No more 
              endless scrolling through irrelevant listings.
            </p>
            <div className="mt-10 flex flex-col gap-4 sm:flex-row sm:justify-center">
              <Link href="/register?role=candidate">
                <Button size="lg" className="gap-2 w-full sm:w-auto">
                  <FileText className="h-5 w-5" />
                  Find Jobs
                </Button>
              </Link>
              <Link href="/register?role=recruiter">
                <Button size="lg" variant="outline" className="gap-2 w-full sm:w-auto">
                  <Users className="h-5 w-5" />
                  Hire Talent
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 bg-muted/30">
        <div className="container mx-auto px-4">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold">How It Works</h2>
            <p className="mt-3 text-muted-foreground">
              Our AI-powered platform makes job matching simple and effective
            </p>
          </div>
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            <Card className="border-0 shadow-sm">
              <CardHeader>
                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10 text-primary mb-2">
                  <FileText className="h-6 w-6" />
                </div>
                <CardTitle className="text-xl">Upload Your Resume</CardTitle>
                <CardDescription>
                  Simply upload your CV in PDF or DOCX format. Our AI extracts your 
                  skills, experience, and qualifications automatically.
                </CardDescription>
              </CardHeader>
            </Card>
            <Card className="border-0 shadow-sm">
              <CardHeader>
                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-accent/10 text-accent mb-2">
                  <Sparkles className="h-6 w-6" />
                </div>
                <CardTitle className="text-xl">AI-Powered Analysis</CardTitle>
                <CardDescription>
                  Our sentence-transformer models create semantic embeddings of your 
                  profile to understand the true essence of your expertise.
                </CardDescription>
              </CardHeader>
            </Card>
            <Card className="border-0 shadow-sm">
              <CardHeader>
                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-chart-3/10 text-chart-3 mb-2">
                  <Target className="h-6 w-6" />
                </div>
                <CardTitle className="text-xl">Smart Matching</CardTitle>
                <CardDescription>
                  Using cosine similarity and skill matching, we find jobs that 
                  align with your profile and show you exactly why they match.
                </CardDescription>
              </CardHeader>
            </Card>
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-20">
        <div className="container mx-auto px-4">
          <div className="grid gap-8 md:grid-cols-3">
            <div className="text-center">
              <div className="text-4xl font-bold text-primary">85%</div>
              <div className="mt-2 text-muted-foreground">Average Match Accuracy</div>
            </div>
            <div className="text-center">
              <div className="text-4xl font-bold text-primary">10K+</div>
              <div className="mt-2 text-muted-foreground">Skills Recognized</div>
            </div>
            <div className="text-center">
              <div className="text-4xl font-bold text-primary">50ms</div>
              <div className="mt-2 text-muted-foreground">Recommendation Speed</div>
            </div>
          </div>
        </div>
      </section>

      {/* For Recruiters Section */}
      <section className="py-20 bg-muted/30">
        <div className="container mx-auto px-4">
          <div className="grid gap-12 lg:grid-cols-2 items-center">
            <div>
              <h2 className="text-3xl font-bold">For Recruiters</h2>
              <p className="mt-4 text-muted-foreground leading-relaxed">
                Post jobs and let our AI match you with qualified candidates. 
                See detailed skill analysis, match scores, and find the perfect 
                fit for your team faster than ever.
              </p>
              <ul className="mt-6 space-y-3">
                <li className="flex items-center gap-3">
                  <div className="flex h-6 w-6 items-center justify-center rounded-full bg-accent text-accent-foreground">
                    <Zap className="h-3.5 w-3.5" />
                  </div>
                  <span>AI-ranked candidate matches</span>
                </li>
                <li className="flex items-center gap-3">
                  <div className="flex h-6 w-6 items-center justify-center rounded-full bg-accent text-accent-foreground">
                    <Zap className="h-3.5 w-3.5" />
                  </div>
                  <span>Detailed skill gap analysis</span>
                </li>
                <li className="flex items-center gap-3">
                  <div className="flex h-6 w-6 items-center justify-center rounded-full bg-accent text-accent-foreground">
                    <Zap className="h-3.5 w-3.5" />
                  </div>
                  <span>Streamlined application review</span>
                </li>
              </ul>
              <Link href="/register?role=recruiter">
                <Button className="mt-8">Start Hiring</Button>
              </Link>
            </div>
            <div className="relative">
              <Card className="border-0 shadow-lg">
                <CardContent className="p-6">
                  <div className="flex items-center justify-between mb-4">
                    <span className="text-sm font-medium">Candidate Match</span>
                    <span className="text-2xl font-bold text-primary">92%</span>
                  </div>
                  <div className="h-2 rounded-full bg-muted overflow-hidden">
                    <div className="h-full w-[92%] rounded-full bg-primary" />
                  </div>
                  <div className="mt-4 space-y-2">
                    <div className="flex items-center gap-2 text-sm">
                      <span className="inline-flex h-5 w-5 items-center justify-center rounded bg-accent/20 text-accent text-xs">8</span>
                      <span className="text-muted-foreground">Matching skills</span>
                    </div>
                    <div className="flex items-center gap-2 text-sm">
                      <span className="inline-flex h-5 w-5 items-center justify-center rounded bg-chart-5/20 text-chart-5 text-xs">2</span>
                      <span className="text-muted-foreground">Skills to develop</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20">
        <div className="container mx-auto px-4 text-center">
          <h2 className="text-3xl font-bold">Ready to Find Your Perfect Match?</h2>
          <p className="mt-4 text-muted-foreground max-w-2xl mx-auto">
            Join thousands of job seekers and recruiters who have transformed their 
            hiring process with AI-powered matching.
          </p>
          <Link href="/register">
            <Button size="lg" className="mt-8">
              Get Started Free
            </Button>
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border py-8">
        <div className="container mx-auto px-4 text-center text-sm text-muted-foreground">
          <p>JobMatch AI - Powered by Sentence Transformers and FAISS</p>
        </div>
      </footer>
    </div>
  );
}
