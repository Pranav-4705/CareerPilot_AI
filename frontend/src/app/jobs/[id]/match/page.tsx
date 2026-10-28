"use client";

import React, { useEffect, useState, useCallback, use } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import {
  getJobApi,
  getResumeApi,
  matchJobResumeApi,
  getMatchInsightsApi,
  JobDescriptionResponse,
  JobMatchResponse,
  ResumeDetailResponse,
  MatchInsightsResponse,
  ApiError,
} from "@/lib/api";

interface JobMatchPageProps {
  params: Promise<{ id: string }>;
}

export default function JobMatchResultsPage({ params }: JobMatchPageProps) {
  const resolvedParams = use(params);
  const jobId = parseInt(resolvedParams.id, 10);

  const searchParams = useSearchParams();
  const resumeIdParam = searchParams.get("resume_id");
  const resumeId = resumeIdParam ? parseInt(resumeIdParam, 10) : null;

  const router = useRouter();
  const { user, token, loading: authLoading, logout, isAuthenticated } = useAuth();

  const [job, setJob] = useState<JobDescriptionResponse | null>(null);
  const [resume, setResume] = useState<ResumeDetailResponse | null>(null);
  const [matchData, setMatchData] = useState<JobMatchResponse | null>(null);
  const [insights, setInsights] = useState<MatchInsightsResponse | null>(null);

  const [loadingMatch, setLoadingMatch] = useState<boolean>(true);
  const [matchError, setMatchError] = useState<string | null>(null);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [authLoading, isAuthenticated, router]);

  const runMatchAndLoadInsights = useCallback(
    async (authToken: string, targetJobId: number, targetResumeId: number) => {
      setLoadingMatch(true);
      setMatchError(null);

      try {
        // 1. Fetch Job
        const jobData = await getJobApi(targetJobId, authToken);
        setJob(jobData);

        // 2. Fetch Resume
        const resumeData = await getResumeApi(targetResumeId, authToken);
        setResume(resumeData);

        // 3. Perform / Ensure Match Record Exists
        const matchResult = await matchJobResumeApi(targetJobId, targetResumeId, authToken);
        setMatchData(matchResult);

        // 4. Fetch Deep Deterministic Match Insights
        const insightsData = await getMatchInsightsApi(targetJobId, targetResumeId, authToken);
        setInsights(insightsData);
      } catch (err) {
        if (err instanceof ApiError) {
          setMatchError(err.message);
        } else {
          setMatchError("We couldn't compute the resume-to-job match insights. Please try again.");
        }
      } finally {
        setLoadingMatch(false);
      }
    },
    []
  );

  useEffect(() => {
    if (token && !isNaN(jobId) && resumeId && !isNaN(resumeId)) {
      runMatchAndLoadInsights(token, jobId, resumeId);
    } else if (!resumeId) {
      setMatchError("Please select a resume version to match against this job description.");
      setLoadingMatch(false);
    }
  }, [token, jobId, resumeId, runMatchAndLoadInsights]);

  if (authLoading || !user) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-slate-950 text-slate-100">
        <div className="flex flex-col items-center space-y-4">
          <div className="animate-spin h-10 w-10 border-3 border-indigo-500 border-t-transparent rounded-full" />
          <p className="text-sm text-slate-400 font-medium animate-pulse">
            Calculating Semantic Compatibility & Gap Insights...
          </p>
        </div>
      </div>
    );
  }

  // Deterministic Match Classification
  const getMatchClassification = (score: number) => {
    if (score >= 90.0) return { label: "Excellent Match", color: "text-emerald-400", bg: "bg-emerald-950/80 border-emerald-700" };
    if (score >= 75.0) return { label: "Strong Match", color: "text-teal-400", bg: "bg-teal-950/80 border-teal-700" };
    if (score >= 60.0) return { label: "Moderate Match", color: "text-amber-400", bg: "bg-amber-950/80 border-amber-700" };
    return { label: "Needs Improvement", color: "text-rose-400", bg: "bg-rose-950/80 border-rose-800" };
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "meets":
        return <span className="px-2.5 py-0.5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800 text-[10px] font-bold uppercase tracking-wider">✓ Meets Criteria</span>;
      case "does_not_meet":
        return <span className="px-2.5 py-0.5 rounded-full bg-rose-950 text-rose-400 border border-rose-800 text-[10px] font-bold uppercase tracking-wider">⚠️ Needs Improvement</span>;
      case "unknown":
        return <span className="px-2.5 py-0.5 rounded-full bg-amber-950 text-amber-400 border border-amber-800 text-[10px] font-bold uppercase tracking-wider">❓ Unclear / Needs Review</span>;
      default:
        return <span className="px-2.5 py-0.5 rounded-full bg-slate-900 text-slate-400 border border-slate-800 text-[10px] font-bold uppercase tracking-wider">Not Specified</span>;
    }
  };

  const getSeverityBadge = (severity: string) => {
    switch (severity) {
      case "critical":
        return <span className="px-2 py-0.5 rounded-md bg-rose-950 text-rose-300 border border-rose-800 text-[10px] font-extrabold uppercase">Critical</span>;
      case "high":
        return <span className="px-2 py-0.5 rounded-md bg-amber-950 text-amber-300 border border-amber-800 text-[10px] font-extrabold uppercase">High</span>;
      case "medium":
        return <span className="px-2 py-0.5 rounded-md bg-indigo-950 text-indigo-300 border border-indigo-800 text-[10px] font-extrabold uppercase">Medium</span>;
      case "info":
        return <span className="px-2 py-0.5 rounded-md bg-teal-950 text-teal-300 border border-teal-800 text-[10px] font-extrabold uppercase">Positive</span>;
      default:
        return <span className="px-2 py-0.5 rounded-md bg-slate-900 text-slate-400 border border-slate-800 text-[10px] font-extrabold uppercase">Low</span>;
    }
  };

  const classification = matchData ? getMatchClassification(matchData.match_score) : null;
  const comp = matchData?.component_scores;

  return (
    <div className="min-h-screen flex flex-col bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 text-slate-100">
      {/* Navigation Header */}
      <header className="border-b border-slate-800/80 backdrop-blur sticky top-0 z-50 bg-slate-950/80">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <Link href="/jobs" className="flex items-center space-x-3 group">
              <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center text-white font-bold shadow-lg shadow-indigo-500/20 group-hover:scale-105 transition-transform">
                CP
              </div>
              <div>
                <span className="text-lg font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-indigo-300 to-purple-400">
                  CareerPilot AI
                </span>
                <span className="ml-2 text-xs uppercase tracking-widest font-semibold px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800/50">
                  Match Insights
                </span>
              </div>
            </Link>
          </div>

          <div className="flex items-center space-x-3 sm:space-x-4">
            <Link
              href={`/jobs/${jobId}`}
              className="text-xs px-3.5 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 font-medium transition flex items-center space-x-1.5"
            >
              <span>← Job Details</span>
            </Link>

            <button
              onClick={() => {
                logout();
                router.push("/login");
              }}
              className="text-xs px-3.5 py-1.5 rounded-xl bg-slate-800/80 hover:bg-rose-900/40 hover:text-rose-300 hover:border-rose-800/60 border border-slate-700/80 text-slate-300 font-medium transition cursor-pointer"
            >
              Sign Out
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 w-full space-y-10">
        {loadingMatch ? (
          <div className="p-16 rounded-2xl bg-slate-900/50 border border-slate-800 flex flex-col items-center justify-center space-y-4">
            <div className="animate-spin h-8 w-8 border-3 border-emerald-500 border-t-transparent rounded-full" />
            <p className="text-sm text-slate-400 font-medium">
              Generating deep deterministic match insights and candidate improvement layer...
            </p>
          </div>
        ) : matchError ? (
          <div className="p-8 rounded-2xl bg-rose-950/30 border border-rose-800/50 text-center space-y-4">
            <div className="h-12 w-12 rounded-2xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-2xl mx-auto text-rose-400">
              ⚠️
            </div>
            <h2 className="text-base font-bold text-white">Matching Error</h2>
            <p className="text-xs text-rose-300 max-w-md mx-auto">{matchError}</p>
            <div className="pt-2">
              <Link
                href={`/jobs/${jobId}`}
                className="px-4 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-xl transition"
              >
                Back to Job Selection
              </Link>
            </div>
          </div>
        ) : matchData && job && resume && classification ? (
          <div className="space-y-10 animate-fadeIn">
            {/* 1. HERO CARD: Overall Match Score & "Why You Matched This Job" */}
            <section className="p-6 sm:p-8 rounded-2xl bg-gradient-to-r from-blue-950/40 via-indigo-950/50 to-purple-950/40 border border-indigo-900/60 shadow-2xl backdrop-blur relative overflow-hidden">
              <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-8 relative z-10">
                {/* Left Overview */}
                <div className="space-y-3 max-w-2xl">
                  <div className="flex items-center space-x-2">
                    <span className="px-2.5 py-0.5 rounded-full bg-blue-950 text-blue-400 border border-blue-800 text-[10px] font-bold uppercase">
                      Target Role #{job.id}
                    </span>
                    <span className="text-slate-500">×</span>
                    <span className="px-2.5 py-0.5 rounded-full bg-indigo-950 text-indigo-400 border border-indigo-800 text-[10px] font-bold uppercase">
                      Resume v{resume.version_number}
                    </span>
                  </div>

                  <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
                    {job.title}
                  </h1>

                  <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-300">
                    {job.company && <span className="font-semibold text-indigo-300">{job.company}</span>}
                    {job.company && <span>•</span>}
                    <span className="font-mono text-slate-400">
                      Evaluated document: {resume.original_filename}
                    </span>
                  </div>
                </div>

                {/* Score Gauge */}
                <div className="flex flex-col items-center lg:items-end justify-center shrink-0">
                  <div className="flex items-baseline space-x-2">
                    <span className="text-5xl sm:text-6xl font-black tracking-tight text-white">
                      {matchData.match_score}
                    </span>
                    <span className="text-xl font-bold text-slate-400">/100</span>
                  </div>

                  <div className={`mt-2 px-3.5 py-1 rounded-full text-xs font-bold uppercase tracking-wider border ${classification.bg} ${classification.color}`}>
                    {classification.label}
                  </div>
                </div>
              </div>

              {/* Quick Component Summary Pills */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-6 pt-6 border-t border-slate-800/80">
                <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/60">
                  <span className="text-[10px] font-bold uppercase text-slate-400 block">Skills Overlap</span>
                  <span className="text-lg font-extrabold text-indigo-400">{comp?.skills_match ?? 0}%</span>
                </div>
                <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/60">
                  <span className="text-[10px] font-bold uppercase text-slate-400 block">Experience Match</span>
                  <span className="text-lg font-extrabold text-blue-400">{comp?.experience_match ?? 0}%</span>
                </div>
                <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/60">
                  <span className="text-[10px] font-bold uppercase text-slate-400 block">Education Match</span>
                  <span className="text-lg font-extrabold text-emerald-400">{comp?.education_match ?? 0}%</span>
                </div>
                <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/60">
                  <span className="text-[10px] font-bold uppercase text-slate-400 block">Responsibility Alignment</span>
                  <span className="text-lg font-extrabold text-teal-400">{comp?.responsibility_match ?? 0}%</span>
                </div>
              </div>
            </section>

            {/* 2. POSITIVE CANDIDATE STRENGTHS */}
            {insights && insights.strengths && insights.strengths.length > 0 && (
              <section className="p-6 sm:p-7 rounded-2xl bg-emerald-950/20 border border-emerald-900/40 shadow-xl space-y-3">
                <div className="flex items-center space-x-2.5 pb-2 border-b border-emerald-900/40">
                  <span className="text-emerald-400 text-lg">⭐</span>
                  <h2 className="text-sm font-bold text-white">Your Strengths for This Role</h2>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                  {insights.strengths.map((str, idx) => (
                    <div key={idx} className="p-3 rounded-xl bg-emerald-950/50 border border-emerald-800/60 text-xs text-emerald-200 flex items-start space-x-2.5">
                      <span className="text-emerald-400 font-bold">✓</span>
                      <span>{str}</span>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* 3. SKILL GAP ANALYSIS SECTION */}
            <section className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2.5">
                  <span className="text-lg">🛠️</span>
                  <h2 className="text-base font-bold text-white tracking-tight">
                    Skill Gap Analysis
                  </h2>
                </div>
                {insights?.skill_gap && (
                  <span className="px-3 py-1 rounded-full bg-indigo-950 text-indigo-300 border border-indigo-800 text-xs font-bold font-mono">
                    Skill Match: {insights.skill_gap.match_percentage}%
                  </span>
                )}
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* Skills You Match */}
                <div className="p-6 sm:p-7 rounded-2xl bg-slate-900/70 border border-slate-800 shadow-xl space-y-4">
                  <div className="flex items-center space-x-2.5 pb-3 border-b border-slate-800">
                    <span className="text-emerald-400 text-lg">✓</span>
                    <div>
                      <h3 className="text-sm font-bold text-white">Skills You Match</h3>
                      <p className="text-[11px] text-slate-400">
                        Technical skills detected in your resume that fulfill the job criteria.
                      </p>
                    </div>
                  </div>

                  {insights?.skill_gap.matched_skills && insights.skill_gap.matched_skills.length > 0 ? (
                    <div className="flex flex-wrap gap-2">
                      {insights.skill_gap.matched_skills.map((skill, idx) => (
                        <span
                          key={idx}
                          className="px-3 py-1 rounded-xl bg-emerald-950/70 border border-emerald-800 text-emerald-200 text-xs font-semibold shadow-sm flex items-center space-x-1.5"
                        >
                          <span className="text-emerald-400">✓</span>
                          <span>{skill}</span>
                        </span>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-slate-500 italic">No direct required skill matches detected.</p>
                  )}
                </div>

                {/* Skills to Work On */}
                <div className="p-6 sm:p-7 rounded-2xl bg-rose-950/20 border border-rose-900/40 shadow-xl space-y-4">
                  <div className="flex items-center space-x-2.5 pb-3 border-b border-rose-900/40">
                    <span className="text-rose-400 text-lg">🔍</span>
                    <div>
                      <h3 className="text-sm font-bold text-white">Skills to Work On</h3>
                      <p className="text-[11px] text-rose-300/80">
                        Technologies required by the posting that were not detected in this resume version.
                      </p>
                    </div>
                  </div>

                  {insights?.skill_gap.prioritized_missing_skills && insights.skill_gap.prioritized_missing_skills.length > 0 ? (
                    <div className="flex flex-wrap gap-2">
                      {insights.skill_gap.prioritized_missing_skills.map((item, idx) => (
                        <span
                          key={idx}
                          className="px-3 py-1 rounded-xl bg-rose-950/70 border border-rose-800 text-rose-200 text-xs font-semibold shadow-sm flex items-center space-x-2"
                        >
                          <span className="text-rose-400 font-bold">+</span>
                          <span>{item.name}</span>
                          <span className="text-[9px] uppercase px-1.5 py-0.2 rounded bg-rose-900/90 text-rose-300 font-mono">
                            {item.priority}
                          </span>
                        </span>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-emerald-400/90 font-medium">
                      ✓ All detected job skills matched in your resume!
                    </p>
                  )}
                </div>
              </div>

              {/* Keyword Gaps & Domain Terminology Alignment */}
              {matchData?.keyword_gaps && matchData.keyword_gaps.length > 0 && (
                <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-2.5">
                  <div className="flex items-center space-x-2">
                    <span className="text-amber-400">🏷️</span>
                    <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                      Relevant Unmatched Domain Keywords
                    </h3>
                  </div>
                  <p className="text-[11px] text-slate-400">
                    Terms frequent in the job description that could improve relevance if included in your experience descriptions:
                  </p>
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {matchData.keyword_gaps.map((kw, idx) => (
                      <span
                        key={idx}
                        className="px-2.5 py-1 rounded-lg bg-slate-950 border border-slate-800 text-amber-300/90 text-xs font-mono"
                      >
                        {kw}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </section>

            {/* 4. EXPERIENCE & EDUCATION INSIGHTS */}
            <section className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              {/* Experience Insight Card */}
              {insights?.experience && (
                <div className="p-6 rounded-2xl bg-slate-900/70 border border-slate-800 shadow-lg space-y-3.5 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                      <div className="flex items-center space-x-2">
                        <span className="text-base">⏳</span>
                        <h3 className="text-xs font-bold text-white uppercase tracking-wider">Experience Evaluation</h3>
                      </div>
                      {getStatusBadge(insights.experience.status)}
                    </div>

                    <div className="mt-3 space-y-1.5 text-xs">
                      <p className="text-slate-400">
                        <strong className="text-slate-200">Requirement:</strong> {insights.experience.requirement}
                      </p>
                      <p className="text-slate-300 leading-relaxed pt-1">
                        {insights.experience.message}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Education Insight Card */}
              {insights?.education && (
                <div className="p-6 rounded-2xl bg-slate-900/70 border border-slate-800 shadow-lg space-y-3.5 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                      <div className="flex items-center space-x-2">
                        <span className="text-base">🎓</span>
                        <h3 className="text-xs font-bold text-white uppercase tracking-wider">Education Qualification</h3>
                      </div>
                      {getStatusBadge(insights.education.status)}
                    </div>

                    <div className="mt-3 space-y-1.5 text-xs">
                      <p className="text-slate-400">
                        <strong className="text-slate-200">Requirement:</strong> {insights.education.requirement}
                      </p>
                      <p className="text-slate-300 leading-relaxed pt-1">
                        {insights.education.message}
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </section>

            {/* 5. RESPONSIBILITY ALIGNMENT */}
            {insights?.responsibilities && (
              <section className="p-6 sm:p-7 rounded-2xl bg-slate-900/70 border border-slate-800 shadow-xl space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                  <div className="flex items-center space-x-2.5">
                    <span className="text-lg">📋</span>
                    <div>
                      <h3 className="text-sm font-bold text-white">Responsibility Alignment</h3>
                      <p className="text-[11px] text-slate-400">
                        Semantic correlation between job duties and your resume project/experience descriptions.
                      </p>
                    </div>
                  </div>
                  <span className="text-xs font-bold font-mono text-teal-400 bg-teal-950/80 border border-teal-800 px-3 py-1 rounded-full">
                    {insights.responsibilities.alignment_score}% Alignment
                  </span>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 pt-2">
                  {/* Aligned Areas */}
                  <div className="space-y-2">
                    <h4 className="text-xs font-bold text-emerald-400 uppercase tracking-wider">
                      ✓ Demonstrated Responsibilities
                    </h4>
                    {insights.responsibilities.aligned_areas.length > 0 ? (
                      <ul className="space-y-2 text-xs text-slate-300">
                        {insights.responsibilities.aligned_areas.map((area, idx) => (
                          <li key={idx} className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 flex items-start space-x-2">
                            <span className="text-emerald-400 font-bold mt-0.5">•</span>
                            <span>{area}</span>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-xs text-slate-500 italic">No specific responsibility overlap detected.</p>
                    )}
                  </div>

                  {/* Areas to Improve */}
                  <div className="space-y-2">
                    <h4 className="text-xs font-bold text-amber-400 uppercase tracking-wider">
                      • Areas for Resume Expansion
                    </h4>
                    {insights.responsibilities.improvement_areas.length > 0 ? (
                      <ul className="space-y-2 text-xs text-slate-300">
                        {insights.responsibilities.improvement_areas.map((area, idx) => (
                          <li key={idx} className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 flex items-start space-x-2">
                            <span className="text-amber-400 font-bold mt-0.5">•</span>
                            <span>{area}</span>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-xs text-emerald-400/90 font-medium">All core job responsibilities reflected in resume.</p>
                    )}
                  </div>
                </div>
              </section>
            )}

            {/* 6. HOW TO IMPROVE YOUR MATCH (ACTIONABLE RECOMMENDATIONS) */}
            {insights?.recommendations && insights.recommendations.length > 0 && (
              <section className="p-6 sm:p-7 rounded-2xl bg-slate-900/70 border border-slate-800 shadow-xl space-y-4">
                <div className="flex items-center space-x-2.5 pb-3 border-b border-slate-800">
                  <span className="text-indigo-400 text-lg">💡</span>
                  <div>
                    <h3 className="text-sm font-bold text-white">How to Improve Your Match</h3>
                    <p className="text-[11px] text-slate-400">
                      Deterministic, prioritized revisions to improve recruiter evaluation and keyword matching.
                    </p>
                  </div>
                </div>

                <div className="space-y-3 pt-1">
                  {insights.recommendations.map((rec, idx) => (
                    <div
                      key={idx}
                      className="p-4 rounded-xl bg-slate-950/80 border border-indigo-950/80 hover:border-indigo-900 transition flex items-start space-x-3.5"
                    >
                      <div className="h-6 w-6 rounded-lg bg-indigo-600/20 text-indigo-400 font-mono text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">
                        {idx + 1}
                      </div>
                      <div className="flex-1 space-y-1.5">
                        <div className="flex items-center space-x-2">
                          {getSeverityBadge(rec.severity)}
                        </div>
                        <p className="text-xs sm:text-sm text-slate-200 leading-relaxed font-medium">
                          {rec.message}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* 7. FOOTER NAVIGATION & RE-MATCHING */}
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-4 border-t border-slate-800">
              <div className="flex flex-wrap items-center gap-3">
                <Link
                  href={`/jobs/${job.id}`}
                  className="px-4 py-2 text-xs font-semibold text-slate-300 hover:text-white bg-slate-900 hover:bg-slate-800 border border-slate-800 rounded-xl transition flex items-center space-x-1.5"
                >
                  <span>🔄 Re-Match Resume</span>
                </Link>
                <Link
                  href={`/resume/${resume.id}/analysis`}
                  className="px-3.5 py-2 text-xs font-semibold text-slate-400 hover:text-slate-200 transition"
                >
                  View Structured Entities
                </Link>
                <Link
                  href={`/resume/${resume.id}/ats`}
                  className="px-3.5 py-2 text-xs font-semibold text-slate-400 hover:text-slate-200 transition"
                >
                  View Resume ATS Score
                </Link>
              </div>

              <div className="flex items-center space-x-3">
                <Link
                  href="/jobs"
                  className="px-5 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-xl transition shadow-lg shadow-indigo-600/25"
                >
                  Back to Jobs Workspace →
                </Link>
              </div>
            </div>
          </div>
        ) : null}
      </main>
    </div>
  );
}
