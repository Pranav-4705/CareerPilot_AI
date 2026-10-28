"use client";

import React, { useEffect, useState, use } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import {
  atsAnalyzeResumeApi,
  getResumeApi,
  ATSAnalysisResponse,
  ResumeDetailResponse,
  ApiError,
} from "@/lib/api";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function ResumeATSPage({ params }: PageProps) {
  const resolvedParams = use(params);
  const resumeId = Number(resolvedParams.id);
  const router = useRouter();
  const { token, loading: authLoading, logout, isAuthenticated } = useAuth();

  const [resume, setResume] = useState<ResumeDetailResponse | null>(null);
  const [atsData, setAtsData] = useState<ATSAnalysisResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [needsStructureAnalysis, setNeedsStructureAnalysis] = useState<boolean>(false);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [authLoading, isAuthenticated, router]);

  const loadATSAnalysis = React.useCallback(async (authToken: string) => {
    if (!resumeId || isNaN(resumeId)) {
      setError("Invalid Resume ID provided.");
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    setNeedsStructureAnalysis(false);

    try {
      // 1. Fetch resume details
      const resumeDetails = await getResumeApi(resumeId, authToken);
      setResume(resumeDetails);

      // 2. Fetch/Compute ATS Analysis
      const results = await atsAnalyzeResumeApi(resumeId, authToken);
      setAtsData(results);
    } catch (err) {
      if (err instanceof ApiError) {
        if (
          err.status === 400 &&
          (err.message.toLowerCase().includes("structurally analyzed") ||
            err.message.toLowerCase().includes("parsed"))
        ) {
          setNeedsStructureAnalysis(true);
        } else {
          setError(err.message);
        }
      } else {
        setError("Failed to generate ATS analysis. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  }, [resumeId]);

  useEffect(() => {
    if (token) {
      loadATSAnalysis(token);
    }
  }, [token, loadATSAnalysis]);

  const getScoreColorInfo = (score: number) => {
    if (score >= 80) {
      return {
        text: "text-emerald-400",
        bg: "bg-emerald-500",
        border: "border-emerald-500/40",
        badge: "bg-emerald-950/80 text-emerald-300 border-emerald-800/80",
        label: "Excellent ATS Compatibility",
        summary: "Your resume meets standard ATS criteria with strong keywords, structure, and readability.",
      };
    } else if (score >= 65) {
      return {
        text: "text-blue-400",
        bg: "bg-blue-500",
        border: "border-blue-500/40",
        badge: "bg-blue-950/80 text-blue-300 border-blue-800/80",
        label: "Solid ATS Score",
        summary: "Good resume structure and skill coverage with a few areas for optimization.",
      };
    } else if (score >= 50) {
      return {
        text: "text-amber-400",
        bg: "bg-amber-500",
        border: "border-amber-500/40",
        badge: "bg-amber-950/80 text-amber-300 border-amber-800/80",
        label: "Needs Optimization",
        summary: "Several important ATS signals or core sections are missing or require refinement.",
      };
    }
    return {
      text: "text-rose-400",
      bg: "bg-rose-500",
      border: "border-rose-500/40",
      badge: "bg-rose-950/80 text-rose-300 border-rose-800/80",
      label: "Low ATS Match",
      summary: "Significant gaps in structure, skills density, or quantifiable metrics detected.",
    };
  };

  if (authLoading || (loading && !atsData && !needsStructureAnalysis)) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-slate-950 text-slate-100">
        <div className="flex flex-col items-center space-y-4">
          <div className="animate-spin h-10 w-10 border-3 border-indigo-500 border-t-transparent rounded-full" />
          <p className="text-sm text-slate-400 font-medium animate-pulse">
            Computing weighted ATS score and extracting improvement signals...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 text-slate-100">
      {/* Header */}
      <header className="border-b border-slate-800/80 backdrop-blur sticky top-0 z-50 bg-slate-950/80">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <Link href="/dashboard" className="flex items-center space-x-3 group">
              <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center text-white font-bold shadow-lg shadow-indigo-500/20 group-hover:scale-105 transition-transform">
                CP
              </div>
              <div>
                <span className="text-lg font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-indigo-300 to-purple-400">
                  CareerPilot AI
                </span>
                <span className="ml-2 text-xs uppercase tracking-widest font-semibold px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800/50">
                  ATS Score
                </span>
              </div>
            </Link>
          </div>

          <div className="flex items-center space-x-3">
            <Link
              href={`/resume/${resumeId}/analysis`}
              className="text-xs px-3.5 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 font-medium transition"
            >
              ← Structured Analysis
            </Link>
            <Link
              href="/dashboard"
              className="text-xs px-3.5 py-1.5 rounded-xl bg-indigo-600/90 hover:bg-indigo-500 text-white font-semibold transition shadow-md shadow-indigo-600/20"
            >
              Dashboard
            </Link>
            <button
              onClick={() => {
                logout();
                router.push("/login");
              }}
              className="text-xs px-3 py-1.5 rounded-xl bg-slate-800/80 hover:bg-rose-900/40 hover:text-rose-300 border border-slate-700/80 text-slate-300 font-medium transition cursor-pointer"
            >
              Sign Out
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full">
        {/* Breadcrumb Navigation */}
        <nav className="flex items-center space-x-2 text-xs text-slate-400 mb-6">
          <Link href="/dashboard" className="hover:text-indigo-400 transition">Dashboard</Link>
          <span>/</span>
          <Link href="/resume" className="hover:text-indigo-400 transition">Resume</Link>
          <span>/</span>
          <Link href={`/resume/${resumeId}/analysis`} className="hover:text-indigo-400 transition">#{resumeId} Analysis</Link>
          <span>/</span>
          <span className="text-slate-200 font-semibold">ATS Score & Improvement</span>
        </nav>

        {/* Needs Structured Analysis Error State */}
        {needsStructureAnalysis && (
          <div className="p-8 rounded-2xl bg-slate-900/80 border border-amber-800/60 text-amber-200 shadow-xl max-w-3xl mx-auto text-center my-10">
            <div className="h-16 w-16 rounded-2xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-3xl mx-auto mb-4 text-amber-400">
              ⚠️
            </div>
            <h2 className="text-xl font-bold text-white mb-2">Structured Analysis Required First</h2>
            <p className="text-xs sm:text-sm text-slate-300 mb-6 max-w-lg mx-auto leading-relaxed">
              Before computing deterministic ATS scores and component insights, your uploaded resume must be structurally analyzed for sections and skills.
            </p>
            <div className="flex justify-center space-x-4">
              <Link
                href={`/resume/${resumeId}/analysis`}
                className="px-6 py-2.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-xl transition shadow-lg shadow-indigo-600/25"
              >
                Run Structured Analysis Now →
              </Link>
              <Link
                href="/resume"
                className="px-5 py-2.5 text-xs font-semibold text-slate-300 bg-slate-800 hover:bg-slate-700 rounded-xl transition"
              >
                Back to Uploads
              </Link>
            </div>
          </div>
        )}

        {/* General Error State */}
        {error && !needsStructureAnalysis && (
          <div className="mb-8 p-6 rounded-2xl bg-rose-950/40 border border-rose-800/60 text-rose-300 shadow-xl">
            <div className="flex items-start space-x-3">
              <span className="text-rose-400 text-xl">❌</span>
              <div className="flex-1">
                <h3 className="text-base font-bold text-rose-200">ATS Evaluation Error</h3>
                <p className="text-xs sm:text-sm mt-1">{error}</p>
                <div className="mt-4 flex space-x-3">
                  <button
                    onClick={() => token && loadATSAnalysis(token)}
                    className="px-4 py-1.5 text-xs font-semibold text-white bg-rose-700 hover:bg-rose-600 rounded-xl transition"
                  >
                    Retry ATS Analysis
                  </button>
                  <Link
                    href={`/resume/${resumeId}/analysis`}
                    className="px-4 py-1.5 text-xs font-semibold text-slate-300 bg-slate-900 hover:bg-slate-800 border border-slate-800 rounded-xl transition"
                  >
                    View Structured Entities
                  </Link>
                </div>
              </div>
            </div>
          </div>
        )}

        {atsData && (
          <div className="space-y-8">
            {/* Top Score Banner & Hero */}
            {(() => {
              const colorInfo = getScoreColorInfo(atsData.ats_score);
              return (
                <div className="p-6 sm:p-8 rounded-2xl bg-slate-900/70 border border-slate-800 shadow-2xl backdrop-blur relative overflow-hidden">
                  <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-8">
                    {/* Left Info */}
                    <div className="max-w-xl">
                      <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-medium mb-3">
                        <span>🎯</span>
                        <span>Deterministic ATS Benchmark</span>
                      </div>
                      <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
                        ATS Resume Score & Evaluation
                      </h1>
                      <p className="text-xs sm:text-sm text-slate-400 mt-1.5 leading-relaxed">
                        Evaluated across 5 transparent weighted dimensions based exclusively on the content found in{" "}
                        <span className="text-slate-200 font-mono font-medium">
                          {resume?.original_filename || `Document #${atsData.resume_id}`}
                        </span>
                        .
                      </p>
                      <p className="text-xs text-slate-300 mt-3 pt-3 border-t border-slate-800/80">
                        {colorInfo.summary}
                      </p>
                    </div>

                    {/* Right Hero Score Dial / Badge */}
                    <div className="flex flex-col sm:flex-row items-center gap-6 p-6 rounded-2xl bg-slate-950/80 border border-slate-800/80 shrink-0">
                      <div className="relative flex items-center justify-center h-28 w-28 rounded-full border-4 border-slate-800 bg-slate-900 shadow-inner">
                        <div className="text-center">
                          <span className={`text-3xl font-black ${colorInfo.text}`}>
                            {atsData.ats_score}
                          </span>
                          <span className="text-[10px] block font-bold text-slate-500 uppercase tracking-widest">
                            / 100
                          </span>
                        </div>
                      </div>

                      <div className="text-center sm:text-left">
                        <span className={`inline-block px-3 py-1 rounded-full text-xs font-bold border uppercase tracking-wider mb-2 ${colorInfo.badge}`}>
                          {colorInfo.label}
                        </span>
                        <div className="flex items-center space-x-2 mt-2">
                          <button
                            onClick={() => token && loadATSAnalysis(token)}
                            disabled={loading}
                            className="px-3.5 py-1.5 text-xs font-semibold text-slate-300 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-xl transition flex items-center space-x-1.5"
                          >
                            <span>🔄</span>
                            <span>Re-Analyze</span>
                          </button>
                          <Link
                            href="/resume"
                            className="px-3.5 py-1.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-xl transition"
                          >
                            + New Upload
                          </Link>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })()}

            {/* 5 Component Breakdown Cards */}
            <section>
              <h2 className="text-sm font-bold uppercase tracking-wider text-slate-400 mb-4 flex items-center space-x-2">
                <span>📊</span>
                <span>Component Score Breakdown</span>
              </h2>

              <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
                {/* 1. Section Structure */}
                <div className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800 shadow-lg flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between text-xs mb-2">
                      <span className="text-slate-400 font-semibold">Section Structure</span>
                      <span className="text-[10px] text-slate-500 font-mono">25% weight</span>
                    </div>
                    <div className="text-2xl font-black text-white mb-2">
                      {atsData.component_scores.section_structure}
                      <span className="text-xs font-medium text-slate-500">/100</span>
                    </div>
                  </div>
                  <div className="w-full bg-slate-950 rounded-full h-2 overflow-hidden border border-slate-800">
                    <div
                      className="bg-blue-500 h-2 rounded-full transition-all duration-500"
                      style={{ width: `${Math.min(100, Math.max(0, atsData.component_scores.section_structure))}%` }}
                    />
                  </div>
                </div>

                {/* 2. Skills Coverage */}
                <div className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800 shadow-lg flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between text-xs mb-2">
                      <span className="text-slate-400 font-semibold">Skills Coverage</span>
                      <span className="text-[10px] text-slate-500 font-mono">25% weight</span>
                    </div>
                    <div className="text-2xl font-black text-white mb-2">
                      {atsData.component_scores.skills_coverage}
                      <span className="text-xs font-medium text-slate-500">/100</span>
                    </div>
                  </div>
                  <div className="w-full bg-slate-950 rounded-full h-2 overflow-hidden border border-slate-800">
                    <div
                      className="bg-indigo-500 h-2 rounded-full transition-all duration-500"
                      style={{ width: `${Math.min(100, Math.max(0, atsData.component_scores.skills_coverage))}%` }}
                    />
                  </div>
                </div>

                {/* 3. Keyword Quality */}
                <div className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800 shadow-lg flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between text-xs mb-2">
                      <span className="text-slate-400 font-semibold">Keyword Quality</span>
                      <span className="text-[10px] text-slate-500 font-mono">20% weight</span>
                    </div>
                    <div className="text-2xl font-black text-white mb-2">
                      {atsData.component_scores.keyword_quality}
                      <span className="text-xs font-medium text-slate-500">/100</span>
                    </div>
                  </div>
                  <div className="w-full bg-slate-950 rounded-full h-2 overflow-hidden border border-slate-800">
                    <div
                      className="bg-purple-500 h-2 rounded-full transition-all duration-500"
                      style={{ width: `${Math.min(100, Math.max(0, atsData.component_scores.keyword_quality))}%` }}
                    />
                  </div>
                </div>

                {/* 4. Experience Depth */}
                <div className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800 shadow-lg flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between text-xs mb-2">
                      <span className="text-slate-400 font-semibold">Experience Depth</span>
                      <span className="text-[10px] text-slate-500 font-mono">20% weight</span>
                    </div>
                    <div className="text-2xl font-black text-white mb-2">
                      {atsData.component_scores.experience_depth}
                      <span className="text-xs font-medium text-slate-500">/100</span>
                    </div>
                  </div>
                  <div className="w-full bg-slate-950 rounded-full h-2 overflow-hidden border border-slate-800">
                    <div
                      className="bg-emerald-500 h-2 rounded-full transition-all duration-500"
                      style={{ width: `${Math.min(100, Math.max(0, atsData.component_scores.experience_depth))}%` }}
                    />
                  </div>
                </div>

                {/* 5. Readability & Formatting */}
                <div className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800 shadow-lg flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between text-xs mb-2">
                      <span className="text-slate-400 font-semibold">Readability / Length</span>
                      <span className="text-[10px] text-slate-500 font-mono">10% weight</span>
                    </div>
                    <div className="text-2xl font-black text-white mb-2">
                      {atsData.component_scores.readability_format}
                      <span className="text-xs font-medium text-slate-500">/100</span>
                    </div>
                  </div>
                  <div className="w-full bg-slate-950 rounded-full h-2 overflow-hidden border border-slate-800">
                    <div
                      className="bg-amber-500 h-2 rounded-full transition-all duration-500"
                      style={{ width: `${Math.min(100, Math.max(0, atsData.component_scores.readability_format))}%` }}
                    />
                  </div>
                </div>
              </div>
            </section>

            {/* Missing Baseline Skills Section */}
            {atsData.missing_skills && atsData.missing_skills.length > 0 && (
              <section className="p-6 sm:p-8 rounded-2xl bg-rose-950/20 border border-rose-900/40 shadow-xl backdrop-blur">
                <div className="flex items-center space-x-3 mb-4 pb-3 border-b border-rose-900/40">
                  <div className="h-8 w-8 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400 text-base">
                    🔍
                  </div>
                  <div>
                    <h2 className="text-base font-bold text-white">Missing Industry Baseline Skills</h2>
                    <p className="text-xs text-rose-300/80">
                      Standard in-demand technologies not detected in your resume. Consider adding them if you possess practical experience.
                    </p>
                  </div>
                </div>

                <div className="flex flex-wrap gap-2.5 pt-2">
                  {atsData.missing_skills.map((skill, idx) => (
                    <span
                      key={idx}
                      className="px-3.5 py-1.5 rounded-xl bg-rose-950/70 border border-rose-800 text-rose-200 text-xs font-semibold shadow-sm flex items-center space-x-1.5"
                    >
                      <span className="text-rose-400 font-bold">+</span>
                      <span>{skill}</span>
                    </span>
                  ))}
                </div>
              </section>
            )}

            {/* Strengths & Weaknesses 2-Column Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              {/* Strengths */}
              <section className="p-6 sm:p-8 rounded-2xl bg-slate-900/70 border border-slate-800 shadow-xl backdrop-blur flex flex-col justify-between">
                <div>
                  <div className="flex items-center space-x-3 mb-6 pb-4 border-b border-slate-800">
                    <div className="h-9 w-9 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 text-lg">
                      ✨
                    </div>
                    <div>
                      <h2 className="text-base font-bold text-white">Identified Strengths</h2>
                      <p className="text-xs text-slate-400">Positive attributes detected by the scoring engine.</p>
                    </div>
                  </div>

                  {atsData.strengths && atsData.strengths.length > 0 ? (
                    <ul className="space-y-3 text-xs">
                      {atsData.strengths.map((str, idx) => (
                        <li
                          key={idx}
                          className="p-3.5 rounded-xl bg-emerald-950/20 border border-emerald-900/30 text-emerald-200 flex items-start space-x-3"
                        >
                          <span className="text-emerald-400 font-bold">✓</span>
                          <span className="leading-relaxed">{str}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-xs text-slate-500 italic">No specific strengths flagged.</p>
                  )}
                </div>
              </section>

              {/* Weaknesses / Gaps */}
              <section className="p-6 sm:p-8 rounded-2xl bg-slate-900/70 border border-slate-800 shadow-xl backdrop-blur flex flex-col justify-between">
                <div>
                  <div className="flex items-center space-x-3 mb-6 pb-4 border-b border-slate-800">
                    <div className="h-9 w-9 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400 text-lg">
                      ⚠️
                    </div>
                    <div>
                      <h2 className="text-base font-bold text-white">Areas for Improvement</h2>
                      <p className="text-xs text-slate-400">Signals where ATS compatibility points were deducted.</p>
                    </div>
                  </div>

                  {atsData.weaknesses && atsData.weaknesses.length > 0 ? (
                    <ul className="space-y-3 text-xs">
                      {atsData.weaknesses.map((weak, idx) => (
                        <li
                          key={idx}
                          className="p-3.5 rounded-xl bg-amber-950/20 border border-amber-900/30 text-amber-200 flex items-start space-x-3"
                        >
                          <span className="text-amber-400 font-bold">•</span>
                          <span className="leading-relaxed">{weak}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <div className="p-4 rounded-xl bg-emerald-950/30 border border-emerald-800/40 text-xs text-emerald-300">
                      ✓ No major weaknesses or structural gaps detected!
                    </div>
                  )}
                </div>
              </section>
            </div>

            {/* Actionable Recommendations */}
            <section className="p-6 sm:p-8 rounded-2xl bg-slate-900/70 border border-slate-800 shadow-xl backdrop-blur">
              <div className="flex items-center space-x-3 mb-6 pb-4 border-b border-slate-800">
                <div className="h-9 w-9 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 text-lg">
                  💡
                </div>
                <div>
                  <h2 className="text-base font-bold text-white">Actionable Improvement Recommendations</h2>
                  <p className="text-xs text-slate-400">
                    Targeted revisions to optimize parsing, keyword indexing, and recruiter evaluation.
                  </p>
                </div>
              </div>

              {atsData.recommendations && atsData.recommendations.length > 0 ? (
                <div className="space-y-3">
                  {atsData.recommendations.map((rec, idx) => (
                    <div
                      key={idx}
                      className="p-4 rounded-xl bg-slate-950/80 border border-indigo-950 hover:border-indigo-800/60 transition flex items-start space-x-3.5"
                    >
                      <div className="h-6 w-6 rounded-lg bg-indigo-600/20 text-indigo-400 font-mono text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">
                        {idx + 1}
                      </div>
                      <p className="text-xs sm:text-sm text-slate-200 leading-relaxed font-medium">
                        {rec}
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-slate-500 italic">No recommendations at this time.</p>
              )}
              {/* Disclaimer */}
              <p className="text-[11px] text-slate-500 italic mt-4 pt-3 border-t border-slate-800/80">
                Note: Recommendations and component scores are evaluated deterministically against standard industry formats and baseline technical taxonomies.
              </p>
            </section>

            {/* Bottom Action Footer */}
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-4 border-t border-slate-800/80">
              <Link
                href={`/resume/${resumeId}/analysis`}
                className="text-xs font-semibold text-slate-300 hover:text-white transition flex items-center space-x-1.5"
              >
                <span>← View Structured Analysis</span>
              </Link>

              <div className="flex items-center space-x-3">
                <Link
                  href="/resume"
                  className="px-4 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-xl transition shadow-lg shadow-indigo-600/25 flex items-center space-x-1.5"
                >
                  <span>Improve Resume / Upload New Version</span>
                  <span>→</span>
                </Link>
                <Link
                  href="/dashboard"
                  className="px-4 py-2 text-xs font-semibold text-slate-300 bg-slate-900 hover:bg-slate-800 border border-slate-800 rounded-xl transition"
                >
                  Back to Dashboard
                </Link>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
