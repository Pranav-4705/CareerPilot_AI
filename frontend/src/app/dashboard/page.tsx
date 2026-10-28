"use client";

import React, { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import {
  getResumesApi,
  getActiveResumeApi,
  activateResumeApi,
  deleteResumeApi,
  ResumeHistoryItem,
  ResumeDetailResponse,
  ApiError,
} from "@/lib/api";

export default function DashboardPage() {
  const router = useRouter();
  const { user, token, loading: authLoading, logout, isAuthenticated } = useAuth();

  const [resumes, setResumes] = useState<ResumeHistoryItem[]>([]);
  const [activeResume, setActiveResume] = useState<ResumeDetailResponse | null>(null);
  const [loadingHistory, setLoadingHistory] = useState<boolean>(true);
  const [historyError, setHistoryError] = useState<string | null>(null);

  // Actions & Modal State
  const [actionLoadingId, setActionLoadingId] = useState<number | null>(null);
  const [actionMessage, setActionMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<ResumeHistoryItem | null>(null);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [authLoading, isAuthenticated, router]);

  const loadResumeData = useCallback(async (authToken: string) => {
    setLoadingHistory(true);
    setHistoryError(null);

    try {
      // 1. Fetch full resume history
      const historyList = await getResumesApi(authToken);
      setResumes(historyList);

      // 2. Fetch currently active resume
      try {
        const active = await getActiveResumeApi(authToken);
        setActiveResume(active);
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) {
          setActiveResume(null);
        } else {
          console.warn("Could not retrieve active resume details:", err);
        }
      }
    } catch (err) {
      if (err instanceof ApiError) {
        setHistoryError(err.message);
      } else {
        setHistoryError("We couldn't load your resume information. Please try again.");
      }
    } finally {
      setLoadingHistory(false);
    }
  }, []);

  useEffect(() => {
    if (token) {
      loadResumeData(token);
    }
  }, [token, loadResumeData]);

  // Handle Activate Resume Version
  const handleActivate = async (resumeId: number) => {
    if (!token) return;
    setActionLoadingId(resumeId);
    setActionMessage(null);

    try {
      await activateResumeApi(resumeId, token);
      setActionMessage({
        type: "success",
        text: `Resume version has been successfully set as active.`,
      });
      await loadResumeData(token);
    } catch (err) {
      setActionMessage({
        type: "error",
        text: err instanceof ApiError ? err.message : "Failed to activate resume version. Please try again.",
      });
    } finally {
      setActionLoadingId(null);
    }
  };

  // Handle Delete Resume Version
  const handleDeleteConfirm = async () => {
    if (!token || !deleteTarget) return;
    const targetId = deleteTarget.id;
    const targetVersion = deleteTarget.version_number;

    setActionLoadingId(targetId);
    setDeleteTarget(null);
    setActionMessage(null);

    try {
      const res = await deleteResumeApi(targetId, token);
      let successText = `Version ${targetVersion} was permanently removed.`;
      if (res.promoted_active_id) {
        successText += ` Resume #${res.promoted_active_id} is now your active version.`;
      }
      setActionMessage({
        type: "success",
        text: successText,
      });
      await loadResumeData(token);
    } catch (err) {
      setActionMessage({
        type: "error",
        text: err instanceof ApiError ? err.message : "Failed to delete resume version. Please try again.",
      });
    } finally {
      setActionLoadingId(null);
    }
  };

  if (authLoading || !user) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-slate-950 text-slate-100">
        <div className="flex flex-col items-center space-y-4">
          <div className="animate-spin h-10 w-10 border-3 border-indigo-500 border-t-transparent rounded-full" />
          <p className="text-sm text-slate-400 font-medium animate-pulse">
            Loading CareerPilot AI Dashboard...
          </p>
        </div>
      </div>
    );
  }

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  const memberSince = user.created_at
    ? new Date(user.created_at).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      })
    : "Recently";

  // Find corresponding active resume item in history for metadata
  const activeHistoryItem = resumes.find((r) => r.is_active);

  return (
    <div className="min-h-screen flex flex-col bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 text-slate-100">
      {/* Dashboard Header */}
      <header className="border-b border-slate-800/80 backdrop-blur sticky top-0 z-50 bg-slate-950/80">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <Link href="/" className="flex items-center space-x-3 group">
              <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center text-white font-bold shadow-lg shadow-indigo-500/20 group-hover:scale-105 transition-transform">
                CP
              </div>
              <div>
                <span className="text-lg font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-indigo-300 to-purple-400">
                  CareerPilot AI
                </span>
                <span className="ml-2 text-xs uppercase tracking-widest font-semibold px-2 py-0.5 rounded-full bg-indigo-950 text-indigo-400 border border-indigo-800/50">
                  Dashboard
                </span>
              </div>
            </Link>
          </div>

          <div className="flex items-center space-x-4">
            {/* User Profile Pill */}
            <div className="hidden sm:flex items-center space-x-3 bg-slate-900 border border-slate-800 rounded-full py-1.5 px-3.5">
              <div className="h-7 w-7 rounded-full bg-indigo-600 flex items-center justify-center text-white text-xs font-bold shadow">
                {user.name.charAt(0).toUpperCase()}
              </div>
              <div className="text-left">
                <p className="text-xs font-semibold text-white leading-tight">
                  {user.name}
                </p>
                <p className="text-[10px] text-slate-400 leading-none truncate max-w-[140px]">
                  {user.email}
                </p>
              </div>
            </div>

            {/* Job Matching Action */}
            <Link
              href="/jobs"
              className="text-xs px-3.5 py-1.5 rounded-xl bg-slate-900 hover:bg-indigo-950/60 border border-slate-800 hover:border-indigo-800/80 text-indigo-300 font-semibold transition shadow-sm"
            >
              🎯 Job Matching
            </Link>

            {/* Technical Interview Action */}
            <Link
              href="/interviews/technical"
              className="text-xs px-3.5 py-1.5 rounded-xl bg-slate-900 hover:bg-purple-950/60 border border-slate-800 hover:border-purple-800/80 text-purple-300 font-semibold transition shadow-sm"
            >
              💻 Tech Round
            </Link>

            {/* HR Interview Action */}
            <Link
              href="/interviews/hr"
              className="text-xs px-3.5 py-1.5 rounded-xl bg-slate-900 hover:bg-emerald-950/60 border border-slate-800 hover:border-emerald-800/80 text-emerald-300 font-semibold transition shadow-sm"
            >
              🤝 HR Round
            </Link>

            {/* Upload Action */}
            <Link
              href="/resume"
              className="text-xs px-3.5 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold transition shadow-md shadow-indigo-600/20"
            >
              + Upload Resume
            </Link>

            {/* Logout Button */}
            <button
              onClick={handleLogout}
              className="text-xs px-3 py-1.5 rounded-xl bg-slate-800/80 hover:bg-rose-900/40 hover:text-rose-300 hover:border-rose-800/60 border border-slate-700/80 text-slate-300 font-medium transition cursor-pointer flex items-center space-x-1.5"
            >
              <span>Logout</span>
              <span>🚪</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Dashboard Content */}
      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full space-y-8">
        {/* Welcome & Overview Header */}
        <section className="p-6 sm:p-8 rounded-2xl bg-gradient-to-r from-blue-950/40 via-indigo-950/40 to-purple-950/30 border border-indigo-900/40 shadow-xl relative overflow-hidden">
          <div className="relative z-10 max-w-3xl">
            <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-medium mb-3">
              <span>👋</span>
              <span>Candidate Intelligence Hub</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight mb-2">
              Welcome back,{" "}
              <span className="bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-indigo-300 to-purple-300">
                {user.name}
              </span>
              !
            </h1>
            <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
              Manage resume iterations, review deterministic parser outputs, benchmark ATS scores, and configure active versions for matching.
            </p>
          </div>
        </section>

        {/* Global Action Banner */}
        {actionMessage && (
          <div
            className={`p-4 rounded-xl text-xs sm:text-sm flex items-center justify-between border ${
              actionMessage.type === "success"
                ? "bg-emerald-950/40 border-emerald-800/60 text-emerald-300"
                : "bg-rose-950/40 border-rose-800/60 text-rose-300"
            }`}
          >
            <div className="flex items-center space-x-2.5">
              <span>{actionMessage.type === "success" ? "✓" : "⚠️"}</span>
              <span>{actionMessage.text}</span>
            </div>
            <button
              onClick={() => setActionMessage(null)}
              className="text-xs opacity-70 hover:opacity-100 font-bold ml-4"
            >
              ✕
            </button>
          </div>
        )}

        {/* SECTION 1: Active Resume Workspace */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-2.5">
              <span className="text-lg">⭐</span>
              <h2 className="text-base font-bold text-white tracking-tight">
                Active Resume
              </h2>
            </div>
            {activeResume && (
              <Link
                href="/resume"
                className="text-xs text-indigo-400 hover:text-indigo-300 font-semibold transition flex items-center space-x-1"
              >
                <span>+ Upload New Version</span>
                <span>→</span>
              </Link>
            )}
          </div>

          {loadingHistory ? (
            <div className="p-8 rounded-2xl bg-slate-900/60 border border-slate-800 flex items-center justify-center space-x-3">
              <div className="animate-spin h-5 w-5 border-2 border-indigo-500 border-t-transparent rounded-full" />
              <span className="text-xs text-slate-400">Loading active resume workspace...</span>
            </div>
          ) : historyError ? (
            <div className="p-6 rounded-2xl bg-rose-950/30 border border-rose-800/50 text-rose-300 flex items-center justify-between">
              <div className="flex items-center space-x-3 text-xs sm:text-sm">
                <span>⚠️</span>
                <span>{historyError}</span>
              </div>
              <button
                onClick={() => token && loadResumeData(token)}
                className="px-3.5 py-1.5 text-xs font-semibold text-white bg-rose-700 hover:bg-rose-600 rounded-xl transition"
              >
                Retry
              </button>
            </div>
          ) : activeResume ? (
            <div className="p-6 sm:p-8 rounded-2xl bg-slate-900/80 border border-indigo-900/60 shadow-xl backdrop-blur relative overflow-hidden">
              <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
                {/* Left Info */}
                <div className="space-y-3 max-w-xl">
                  <div className="flex items-center space-x-2.5">
                    <span className="px-2.5 py-0.5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800/80 text-[10px] font-extrabold uppercase tracking-wider flex items-center space-x-1.5 shadow-sm">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                      <span>ACTIVE VERSION {activeResume.version_number}</span>
                    </span>
                    <span className="text-xs text-slate-400 font-mono">
                      #{activeResume.id}
                    </span>
                  </div>

                  <h3 className="text-xl sm:text-2xl font-bold text-white tracking-tight flex items-center space-x-2">
                    <span>📄</span>
                    <span className="truncate">{activeResume.original_filename}</span>
                  </h3>

                  <p className="text-xs text-slate-400 flex items-center space-x-3">
                    <span>
                      Uploaded on{" "}
                      {new Date(activeResume.uploaded_at).toLocaleDateString("en-US", {
                        month: "short",
                        day: "numeric",
                        year: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                  </p>

                  {/* Status Pills */}
                  <div className="flex flex-wrap items-center gap-2 pt-1">
                    {activeHistoryItem?.is_parsed ? (
                      <span className="px-2.5 py-1 rounded-lg bg-blue-950/60 border border-blue-800/60 text-blue-300 text-[11px] font-medium flex items-center space-x-1">
                        <span>✓</span>
                        <span>Text Parsed</span>
                      </span>
                    ) : (
                      <span className="px-2.5 py-1 rounded-lg bg-amber-950/60 border border-amber-800/60 text-amber-300 text-[11px] font-medium">
                        Resume uploaded successfully (Unparsed)
                      </span>
                    )}

                    {activeHistoryItem?.has_analysis ? (
                      <span className="px-2.5 py-1 rounded-lg bg-indigo-950/60 border border-indigo-800/60 text-indigo-300 text-[11px] font-medium flex items-center space-x-1">
                        <span>✓</span>
                        <span>Structured Analysis Complete</span>
                      </span>
                    ) : activeHistoryItem?.is_parsed ? (
                      <span className="px-2.5 py-1 rounded-lg bg-slate-950 border border-slate-800 text-slate-400 text-[11px]">
                        Analysis Pending
                      </span>
                    ) : null}

                    {activeHistoryItem?.has_ats_score && activeHistoryItem.ats_score !== null ? (
                      <span className="px-2.5 py-1 rounded-lg bg-emerald-950/80 border border-emerald-700/80 text-emerald-300 text-[11px] font-bold flex items-center space-x-1">
                        <span>🎯</span>
                        <span>ATS Score: {activeHistoryItem.ats_score}/100</span>
                      </span>
                    ) : activeHistoryItem?.has_analysis ? (
                      <span className="px-2.5 py-1 rounded-lg bg-slate-950 border border-slate-800 text-slate-400 text-[11px]">
                        ATS Not Evaluated
                      </span>
                    ) : null}
                  </div>
                </div>

                {/* Right Contextual Workflow Actions (States B, C, D, E) */}
                <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 shrink-0">
                  {/* State E: ATS Analysis Complete */}
                  {activeHistoryItem?.has_ats_score ? (
                    <>
                      <Link
                        href={`/resume/${activeResume.id}/ats`}
                        className="px-5 py-2.5 text-xs font-semibold text-white bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 rounded-xl shadow-lg shadow-emerald-600/25 transition text-center flex items-center justify-center space-x-2"
                      >
                        <span>🎯 View ATS Results</span>
                        <span>→</span>
                      </Link>
                      <Link
                        href={`/resume/${activeResume.id}/analysis`}
                        className="px-4 py-2.5 text-xs font-semibold text-slate-300 bg-slate-900 hover:bg-slate-800 border border-slate-800 rounded-xl transition text-center"
                      >
                        View Structured Analysis
                      </Link>
                      <Link
                        href="/resume"
                        className="px-4 py-2.5 text-xs font-semibold text-slate-400 hover:text-white bg-slate-950 hover:bg-slate-900 border border-slate-800 rounded-xl transition text-center"
                      >
                        + Upload New Version
                      </Link>
                    </>
                  ) : activeHistoryItem?.has_analysis ? (
                    /* State D: Structured Analysis Complete but ATS Not Evaluated */
                    <>
                      <Link
                        href={`/resume/${activeResume.id}/ats`}
                        className="px-5 py-2.5 text-xs font-semibold text-white bg-gradient-to-r from-emerald-600 to-indigo-600 hover:from-emerald-500 hover:to-indigo-500 rounded-xl shadow-lg shadow-emerald-600/25 transition text-center flex items-center justify-center space-x-2"
                      >
                        <span>⚡ Run ATS Analysis</span>
                        <span>→</span>
                      </Link>
                      <Link
                        href={`/resume/${activeResume.id}/analysis`}
                        className="px-4 py-2.5 text-xs font-semibold text-slate-300 bg-slate-900 hover:bg-slate-800 border border-slate-800 rounded-xl transition text-center"
                      >
                        View Structured Analysis
                      </Link>
                    </>
                  ) : activeHistoryItem?.is_parsed ? (
                    /* State C: Resume Parsed but Not Structurally Analyzed */
                    <>
                      <Link
                        href={`/resume/${activeResume.id}/analysis`}
                        className="px-5 py-2.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-xl shadow-lg shadow-indigo-600/25 transition text-center flex items-center justify-center space-x-2"
                      >
                        <span>🔍 Analyze Resume</span>
                        <span>→</span>
                      </Link>
                    </>
                  ) : (
                    /* State B: Resume Uploaded but Not Parsed */
                    <>
                      <Link
                        href="/resume"
                        className="px-5 py-2.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-500 rounded-xl shadow-lg shadow-blue-600/25 transition text-center flex items-center justify-center space-x-2"
                      >
                        <span>⚡ Parse Resume</span>
                        <span>→</span>
                      </Link>
                    </>
                  )}

                  {/* Delete Active Button */}
                  {activeHistoryItem && (
                    <button
                      type="button"
                      onClick={() => setDeleteTarget(activeHistoryItem)}
                      disabled={actionLoadingId === activeResume.id}
                      className="px-3.5 py-2.5 text-xs font-semibold text-rose-400 hover:text-rose-200 bg-rose-950/30 hover:bg-rose-900/50 border border-rose-900/50 rounded-xl transition text-center disabled:opacity-50"
                    >
                      Delete
                    </button>
                  )}
                </div>
              </div>
            </div>
          ) : (
            /* State A — No Resume */
            <div className="p-8 rounded-2xl bg-slate-900/60 border border-dashed border-slate-800 text-center space-y-3">
              <div className="h-12 w-12 rounded-2xl bg-indigo-600/10 border border-indigo-500/20 flex items-center justify-center text-2xl mx-auto text-indigo-400">
                📄
              </div>
              <h3 className="text-base font-bold text-white">No resumes uploaded yet</h3>
              <p className="text-xs text-slate-400 max-w-sm mx-auto">
                Your resume is the starting point for your CareerPilot analysis.
              </p>
              <div className="pt-2">
                <Link
                  href="/resume"
                  className="inline-flex items-center space-x-2 px-5 py-2.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-xl shadow-lg shadow-indigo-600/25 transition"
                >
                  <span>Upload Your Resume</span>
                  <span>→</span>
                </Link>
              </div>
            </div>
          )}
        </section>

        {/* SECTION 2: Target Role & Job Matching Intelligence */}
        <section className="p-6 rounded-2xl bg-gradient-to-r from-slate-900 via-indigo-950/40 to-slate-900 border border-indigo-900/40 shadow-xl flex flex-col sm:flex-row sm:items-center justify-between gap-5">
          <div className="space-y-1.5 max-w-xl">
            <div className="flex items-center space-x-2">
              <span className="text-base">🎯</span>
              <h2 className="text-sm font-bold text-white tracking-tight">
                Target Role & Job Description Matching
              </h2>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              Compare your candidate profile against live target job postings. Evaluate skills coverage, requirement gaps, and keyword alignment.
            </p>
          </div>

          <Link
            href="/jobs"
            className="px-5 py-2.5 text-xs font-semibold text-white bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 rounded-xl shadow-lg shadow-indigo-600/25 transition text-center shrink-0 flex items-center justify-center space-x-2"
          >
            <span>🎯 Match Resume to a Job</span>
            <span>→</span>
          </Link>
        </section>

        {/* SECTION 2.5: AI Technical Interview */}
        <section className="p-6 rounded-2xl bg-gradient-to-r from-slate-900 via-purple-950/40 to-slate-900 border border-purple-900/40 shadow-xl flex flex-col sm:flex-row sm:items-center justify-between gap-5">
          <div className="space-y-1.5 max-w-xl">
            <div className="flex items-center space-x-2">
              <span className="text-base">🎤</span>
              <h2 className="text-sm font-bold text-white tracking-tight">
                AI Technical Interview Practice
              </h2>
              <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-purple-950 text-purple-300 border border-purple-800/40">
                Phase 8
              </span>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              Experience an adaptive technical interview tailored to your claimed resume projects, skills, and target job descriptions. Powered by Google Gemini with real-time feedback.
            </p>
          </div>

          <Link
            href="/interviews/technical"
            className="px-5 py-2.5 text-xs font-semibold text-white bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 rounded-xl shadow-lg shadow-purple-600/25 transition text-center shrink-0 flex items-center justify-center space-x-2"
          >
            <span>💻 Start Technical Interview</span>
            <span>→</span>
          </Link>
        </section>

        {/* SECTION 2.6: AI HR & Behavioral Interview */}
        <section className="p-6 rounded-2xl bg-gradient-to-r from-slate-900 via-emerald-950/40 to-slate-900 border border-emerald-900/40 shadow-xl flex flex-col sm:flex-row sm:items-center justify-between gap-5">
          <div className="space-y-1.5 max-w-xl">
            <div className="flex items-center space-x-2">
              <span className="text-base">🤝</span>
              <h2 className="text-sm font-bold text-white tracking-tight">
                AI HR & Behavioral Interview Practice
              </h2>
              <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-300 border border-emerald-800/40">
                Phase 9
              </span>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              Practice behavioral questions, teamwork, leadership scenarios, and cultural fit grounded in your real resume experience. Evaluated across 6 dimensions with STAR feedback.
            </p>
          </div>

          <Link
            href="/interviews/hr"
            className="px-5 py-2.5 text-xs font-semibold text-white bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 rounded-xl shadow-lg shadow-emerald-600/25 transition text-center shrink-0 flex items-center justify-center space-x-2"
          >
            <span>🤝 Start HR Interview</span>
            <span>→</span>
          </Link>
        </section>

        {/* SECTION 3: Resume History List */}
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2.5">
              <span className="text-lg">📚</span>
              <h2 className="text-base font-bold text-white tracking-tight">
                Resume Version History
              </h2>
              {resumes.length > 0 && (
                <span className="px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 text-[10px] font-bold">
                  {resumes.length} {resumes.length === 1 ? "version" : "versions"}
                </span>
              )}
            </div>
          </div>

          {loadingHistory ? (
            <div className="p-6 rounded-2xl bg-slate-900/40 border border-slate-800 text-center text-xs text-slate-400">
              Loading resume history...
            </div>
          ) : resumes.length === 0 ? (
            <div className="p-6 rounded-xl bg-slate-950/40 border border-slate-800/80 text-center text-xs text-slate-500">
              Historical uploads will appear here as you upload new versions.
            </div>
          ) : (
            <div className="space-y-3">
              {resumes.map((item) => {
                const isItemActionLoading = actionLoadingId === item.id;
                return (
                  <div
                    key={item.id}
                    className={`p-4 sm:p-5 rounded-xl border transition flex flex-col sm:flex-row sm:items-center justify-between gap-4 ${
                      item.is_active
                        ? "bg-slate-900/90 border-indigo-900/70 shadow-md"
                        : "bg-slate-950/70 border-slate-800/80 hover:border-slate-700"
                    }`}
                  >
                    {/* Item Left Info */}
                    <div className="space-y-1.5 min-w-0">
                      <div className="flex items-center space-x-2">
                        <span className="px-2 py-0.5 rounded-md bg-slate-800 border border-slate-700 text-slate-300 font-mono text-[10px] font-bold uppercase">
                          v{item.version_number}
                        </span>
                        {item.is_active ? (
                          <span className="px-2 py-0.5 rounded-md bg-emerald-950 text-emerald-400 border border-emerald-800 text-[10px] font-bold uppercase">
                            Active
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded-md bg-slate-900 text-slate-500 border border-slate-800 text-[10px] uppercase">
                            Archived
                          </span>
                        )}
                        <span className="text-xs font-semibold text-white truncate max-w-xs sm:max-w-md">
                          {item.original_filename}
                        </span>
                      </div>

                      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-slate-400">
                        <span>
                          Uploaded:{" "}
                          {new Date(item.uploaded_at).toLocaleDateString("en-US", {
                            month: "short",
                            day: "numeric",
                            year: "numeric",
                          })}
                        </span>
                        <span>•</span>
                        {item.has_ats_score && item.ats_score !== null ? (
                          <span className="font-semibold text-emerald-400">
                            ATS Score: {item.ats_score}/100
                          </span>
                        ) : item.has_analysis ? (
                          <span className="text-indigo-300">Structured Analysis Ready</span>
                        ) : item.is_parsed ? (
                          <span className="text-blue-300">Parsed Text Ready</span>
                        ) : (
                          <span className="text-slate-500">Unparsed Document</span>
                        )}
                      </div>
                    </div>

                    {/* Item Right Actions */}
                    <div className="flex items-center space-x-2 shrink-0">
                      {/* Set as Active (for inactive versions) */}
                      {!item.is_active && (
                        <button
                          type="button"
                          onClick={() => handleActivate(item.id)}
                          disabled={isItemActionLoading}
                          className="px-3 py-1.5 text-xs font-semibold text-indigo-300 hover:text-white bg-indigo-950/60 hover:bg-indigo-900/80 border border-indigo-800/80 rounded-lg transition disabled:opacity-50 flex items-center space-x-1"
                        >
                          {isItemActionLoading ? (
                            <>
                              <div className="animate-spin h-3 w-3 border border-indigo-300 border-t-transparent rounded-full" />
                              <span>Activating...</span>
                            </>
                          ) : (
                            <span>Set as Active</span>
                          )}
                        </button>
                      )}

                      {/* View Analysis */}
                      <Link
                        href={`/resume/${item.id}/analysis`}
                        className="px-3 py-1.5 text-xs font-semibold text-slate-300 hover:text-white bg-slate-900 hover:bg-slate-800 border border-slate-800 rounded-lg transition"
                      >
                        Analysis
                      </Link>

                      {/* View / Run ATS */}
                      {item.has_ats_score ? (
                        <Link
                          href={`/resume/${item.id}/ats`}
                          className="px-3 py-1.5 text-xs font-semibold text-emerald-300 hover:text-white bg-emerald-950/60 hover:bg-emerald-900/80 border border-emerald-800/80 rounded-lg transition"
                        >
                          ATS Results
                        </Link>
                      ) : item.has_analysis ? (
                        <Link
                          href={`/resume/${item.id}/ats`}
                          className="px-3 py-1.5 text-xs font-semibold text-indigo-300 hover:text-white bg-indigo-950/60 hover:bg-indigo-900/80 border border-indigo-800/80 rounded-lg transition"
                        >
                          Run ATS
                        </Link>
                      ) : null}

                      {/* Delete Action */}
                      <button
                        type="button"
                        onClick={() => setDeleteTarget(item)}
                        disabled={isItemActionLoading}
                        className="px-2.5 py-1.5 text-xs font-medium text-slate-500 hover:text-rose-400 hover:bg-rose-950/30 rounded-lg transition disabled:opacity-50"
                        title="Delete resume version"
                      >
                        🗑️
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>

        {/* SECTION 3: Account & Session Info */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 pt-4 border-t border-slate-800/80">
          <div className="p-6 rounded-2xl bg-slate-900/50 border border-slate-800">
            <div className="flex items-center space-x-3 mb-3">
              <span className="text-base">👤</span>
              <h3 className="text-sm font-semibold text-white">Candidate Account</h3>
            </div>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div>
                <span className="text-slate-500 block uppercase text-[10px] font-bold">Candidate Name</span>
                <span className="text-white font-medium">{user.name}</span>
              </div>
              <div>
                <span className="text-slate-500 block uppercase text-[10px] font-bold">Email Address</span>
                <span className="text-slate-300 font-mono truncate block">{user.email}</span>
              </div>
              <div>
                <span className="text-slate-500 block uppercase text-[10px] font-bold">Member Since</span>
                <span className="text-slate-300">{memberSince}</span>
              </div>
              <div>
                <span className="text-slate-500 block uppercase text-[10px] font-bold">Candidate ID</span>
                <span className="text-indigo-400 font-mono font-bold">#{user.id}</span>
              </div>
            </div>
          </div>

          <div className="p-6 rounded-2xl bg-slate-900/50 border border-slate-800 flex flex-col justify-between">
            <div>
              <div className="flex items-center space-x-3 mb-3">
                <span className="text-base">🔒</span>
                <h3 className="text-sm font-semibold text-white">Active Session Security</h3>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                Your session is protected with JWT bearer authentication. Signing out clears local tokens and terminates the active session.
              </p>
            </div>
            <div className="mt-4 pt-3 border-t border-slate-800/60">
              <button
                onClick={handleLogout}
                className="w-full py-2 px-3 rounded-xl bg-slate-800 hover:bg-rose-950/40 text-slate-300 hover:text-rose-300 border border-slate-700 hover:border-rose-900/50 text-xs font-semibold transition cursor-pointer"
              >
                Sign Out of CareerPilot AI
              </button>
            </div>
          </div>
        </div>
      </main>

      {/* Confirmation Modal: Delete Resume Version */}
      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-rose-900/60 rounded-2xl p-6 sm:p-8 max-w-md w-full shadow-2xl space-y-4 animate-fadeIn">
            <div className="flex items-center space-x-3">
              <div className="h-10 w-10 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400 text-lg">
                ⚠️
              </div>
              <div>
                <h3 className="text-base font-bold text-white">Delete Resume Version?</h3>
                <p className="text-xs text-slate-400">
                  Version {deleteTarget.version_number} • {deleteTarget.original_filename}
                </p>
              </div>
            </div>

            <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
              This will permanently remove this resume version, its extracted text, structured analysis, ATS scores, and stored file from disk. This action cannot be undone.
            </p>

            {deleteTarget.is_active && (
              <div className="p-3 rounded-xl bg-amber-950/30 border border-amber-800/50 text-[11px] text-amber-300">
                ⭐ <strong>Active Resume Note:</strong> Deleting this version will automatically promote your newest remaining resume to active.
              </div>
            )}

            <div className="flex items-center justify-end space-x-3 pt-2">
              <button
                type="button"
                onClick={() => setDeleteTarget(null)}
                disabled={actionLoadingId === deleteTarget.id}
                className="px-4 py-2 text-xs font-semibold text-slate-300 bg-slate-800 hover:bg-slate-700 rounded-xl transition disabled:opacity-50"
              >
                Cancel
              </button>

              <button
                type="button"
                onClick={handleDeleteConfirm}
                disabled={actionLoadingId === deleteTarget.id}
                className="px-4 py-2 text-xs font-semibold text-white bg-rose-600 hover:bg-rose-500 rounded-xl shadow-lg shadow-rose-600/25 transition disabled:opacity-50 flex items-center space-x-1.5"
              >
                {actionLoadingId === deleteTarget.id ? (
                  <>
                    <div className="animate-spin h-3.5 w-3.5 border-2 border-white border-t-transparent rounded-full" />
                    <span>Deleting...</span>
                  </>
                ) : (
                  <span>Delete Permanently</span>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
