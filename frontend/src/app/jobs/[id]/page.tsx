"use client";

import React, { useEffect, useState, useCallback, use } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import {
  getJobApi,
  analyzeJobApi,
  getResumesApi,
  matchJobResumeApi,
  JobDescriptionResponse,
  ResumeHistoryItem,
  ApiError,
} from "@/lib/api";

interface JobDetailPageProps {
  params: Promise<{ id: string }>;
}

export default function JobDetailPage({ params }: JobDetailPageProps) {
  const resolvedParams = use(params);
  const jobId = parseInt(resolvedParams.id, 10);

  const router = useRouter();
  const { user, token, loading: authLoading, logout, isAuthenticated } = useAuth();

  const [job, setJob] = useState<JobDescriptionResponse | null>(null);
  const [resumes, setResumes] = useState<ResumeHistoryItem[]>([]);
  const [selectedResumeId, setSelectedResumeId] = useState<number | null>(null);

  const [loadingJob, setLoadingJob] = useState<boolean>(true);
  const [analyzingJob, setAnalyzingJob] = useState<boolean>(false);
  const [matchingInProgress, setMatchingInProgress] = useState<boolean>(false);

  const [errorBanner, setErrorBanner] = useState<string | null>(null);
  const [successBanner, setSuccessBanner] = useState<string | null>(null);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [authLoading, isAuthenticated, router]);

  const loadData = useCallback(async (authToken: string) => {
    setLoadingJob(true);
    setErrorBanner(null);

    try {
      // 1. Fetch Job
      const jobData = await getJobApi(jobId, authToken);
      setJob(jobData);

      // 2. Fetch Resumes
      try {
        const resumeList = await getResumesApi(authToken);
        setResumes(resumeList);
        // Default select the active resume if present
        const activeRes = resumeList.find((r) => r.is_active);
        if (activeRes) {
          setSelectedResumeId(activeRes.id);
        } else if (resumeList.length > 0) {
          setSelectedResumeId(resumeList[0].id);
        }
      } catch (err) {
        console.warn("Could not load candidate resumes:", err);
      }
    } catch (err) {
      if (err instanceof ApiError) {
        setErrorBanner(err.message);
      } else {
        setErrorBanner("We couldn't load this job description. Please try again.");
      }
    } finally {
      setLoadingJob(false);
    }
  }, [jobId]);

  useEffect(() => {
    if (token && !isNaN(jobId)) {
      loadData(token);
    }
  }, [token, jobId, loadData]);

  // Handle Analyze Job Description
  const handleAnalyzeJob = async () => {
    if (!token || !job) return;
    setAnalyzingJob(true);
    setErrorBanner(null);
    setSuccessBanner(null);

    try {
      await analyzeJobApi(job.id, token);
      setSuccessBanner("Job description analyzed successfully! Structured requirements extracted.");
      // Reload job data
      const updatedJob = await getJobApi(job.id, token);
      setJob(updatedJob);
    } catch (err) {
      if (err instanceof ApiError) {
        setErrorBanner(err.message);
      } else {
        setErrorBanner("Failed to analyze job requirements. Please try again.");
      }
    } finally {
      setAnalyzingJob(false);
    }
  };

  // Handle Match Resume to Job
  const handleMatchResume = async () => {
    if (!token || !job || !selectedResumeId) return;

    const selectedResume = resumes.find((r) => r.id === selectedResumeId);
    if (!selectedResume?.has_analysis) {
      setErrorBanner("This resume needs structured analysis before job matching. Please analyze the resume first.");
      return;
    }

    setMatchingInProgress(true);
    setErrorBanner(null);

    try {
      await matchJobResumeApi(job.id, selectedResumeId, token);
      router.push(`/jobs/${job.id}/match?resume_id=${selectedResumeId}`);
    } catch (err) {
      if (err instanceof ApiError) {
        setErrorBanner(err.message);
      } else {
        setErrorBanner("Failed to perform resume-to-job matching. Please try again.");
      }
      setMatchingInProgress(false);
    }
  };

  if (authLoading || !user) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-slate-950 text-slate-100">
        <div className="flex flex-col items-center space-y-4">
          <div className="animate-spin h-10 w-10 border-3 border-indigo-500 border-t-transparent rounded-full" />
          <p className="text-sm text-slate-400 font-medium animate-pulse">
            Loading Job & Match Workspace...
          </p>
        </div>
      </div>
    );
  }

  const isAnalyzed = Boolean(job?.extracted_skills && job.extracted_skills.length > 0);
  const selectedResume = resumes.find((r) => r.id === selectedResumeId);

  // Parse experience signals
  let expSignals: string[] = [];
  if (job?.required_experience) {
    if (Array.isArray(job.required_experience)) {
      expSignals = job.required_experience;
    } else if (typeof job.required_experience === "object" && "signals" in job.required_experience) {
      expSignals = (job.required_experience as { signals: string[] }).signals || [];
    }
  }

  return (
    <div className="min-h-screen flex flex-col bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 text-slate-100">
      {/* Header */}
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
                <span className="ml-2 text-xs uppercase tracking-widest font-semibold px-2 py-0.5 rounded-full bg-blue-950 text-blue-400 border border-blue-800/50">
                  Job Match
                </span>
              </div>
            </Link>
          </div>

          <div className="flex items-center space-x-3 sm:space-x-4">
            <Link
              href="/jobs"
              className="text-xs px-3.5 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 font-medium transition flex items-center space-x-1.5"
            >
              <span>← All Jobs</span>
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
      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 w-full space-y-8">
        {/* Banner Alerts */}
        {errorBanner && (
          <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800/60 text-rose-300 text-xs sm:text-sm flex items-center justify-between">
            <div className="flex items-center space-x-2.5">
              <span>⚠️</span>
              <span>{errorBanner}</span>
            </div>
            <button onClick={() => setErrorBanner(null)} className="opacity-70 hover:opacity-100 font-bold ml-4">✕</button>
          </div>
        )}

        {successBanner && (
          <div className="p-4 rounded-xl bg-emerald-950/40 border border-emerald-800/60 text-emerald-300 text-xs sm:text-sm flex items-center justify-between">
            <div className="flex items-center space-x-2.5">
              <span>✓</span>
              <span>{successBanner}</span>
            </div>
            <button onClick={() => setSuccessBanner(null)} className="opacity-70 hover:opacity-100 font-bold ml-4">✕</button>
          </div>
        )}

        {loadingJob ? (
          <div className="p-12 rounded-2xl bg-slate-900/50 border border-slate-800 flex items-center justify-center space-x-3">
            <div className="animate-spin h-6 w-6 border-2 border-indigo-500 border-t-transparent rounded-full" />
            <span className="text-sm text-slate-400">Loading target job details...</span>
          </div>
        ) : !job ? (
          <div className="p-12 rounded-2xl bg-slate-900/40 border border-dashed border-slate-800 text-center space-y-4">
            <h3 className="text-base font-bold text-white">Job Posting Not Found</h3>
            <p className="text-xs text-slate-400">This job posting may have been removed or does not belong to your account.</p>
            <Link href="/jobs" className="inline-block px-4 py-2 text-xs font-semibold text-white bg-indigo-600 rounded-xl">
              Return to Jobs
            </Link>
          </div>
        ) : (
          <>
            {/* Top Job Overview Card */}
            <section className="p-6 sm:p-8 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-xl backdrop-blur relative overflow-hidden">
              <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 relative z-10">
                <div className="space-y-2">
                  <div className="flex items-center space-x-2">
                    <span className="px-2.5 py-0.5 rounded-full bg-blue-950 text-blue-400 border border-blue-800 text-[10px] font-bold uppercase tracking-wider">
                      Target Role #{job.id}
                    </span>
                    {isAnalyzed ? (
                      <span className="px-2.5 py-0.5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800 text-[10px] font-bold uppercase">
                        ✓ Analyzed
                      </span>
                    ) : (
                      <span className="px-2.5 py-0.5 rounded-full bg-amber-950 text-amber-400 border border-amber-800 text-[10px] font-bold uppercase">
                        Pending Analysis
                      </span>
                    )}
                  </div>

                  <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
                    {job.title}
                  </h1>

                  <p className="text-xs text-slate-400 flex items-center space-x-3">
                    {job.company && <span className="font-semibold text-indigo-300">{job.company}</span>}
                    {job.company && <span>•</span>}
                    <span>
                      Created:{" "}
                      {new Date(job.created_at).toLocaleDateString("en-US", {
                        month: "short",
                        day: "numeric",
                        year: "numeric",
                      })}
                    </span>
                  </p>
                </div>

                {/* Top Action */}
                <div className="shrink-0">
                  <button
                    type="button"
                    onClick={handleAnalyzeJob}
                    disabled={analyzingJob}
                    className="px-5 py-2.5 text-xs font-semibold text-white bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 rounded-xl shadow-lg shadow-indigo-600/25 transition disabled:opacity-50 flex items-center space-x-2"
                  >
                    {analyzingJob ? (
                      <>
                        <div className="animate-spin h-3.5 w-3.5 border-2 border-white border-t-transparent rounded-full" />
                        <span>Extracting Requirements...</span>
                      </>
                    ) : isAnalyzed ? (
                      <>
                        <span>🔄 Re-Analyze Job</span>
                      </>
                    ) : (
                      <>
                        <span>⚡ Analyze Job Description</span>
                        <span>→</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            </section>

            {/* 2-Column: Structured Requirements (Left) & Resume Selection (Right) */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
              {/* Left Column: Extracted Job Requirements */}
              <div className="lg:col-span-7 space-y-6">
                {/* Extracted Skills */}
                <section className="p-6 rounded-2xl bg-slate-900/70 border border-slate-800 shadow-lg space-y-3">
                  <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                    <div className="flex items-center space-x-2">
                      <span className="text-base">🛠️</span>
                      <h2 className="text-sm font-bold text-white">Required Technical Skills</h2>
                    </div>
                    {job.extracted_skills && (
                      <span className="text-[11px] font-mono text-indigo-400">
                        {job.extracted_skills.length} detected
                      </span>
                    )}
                  </div>

                  {job.extracted_skills && job.extracted_skills.length > 0 ? (
                    <div className="flex flex-wrap gap-2 pt-1">
                      {job.extracted_skills.map((skill, idx) => (
                        <span
                          key={idx}
                          className="px-3 py-1 rounded-xl bg-indigo-950/70 border border-indigo-800 text-indigo-200 text-xs font-semibold shadow-sm"
                        >
                          {skill}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-slate-500 italic">
                      {isAnalyzed ? "No specific skills detected in job text." : "Run job analysis to extract technical skills."}
                    </p>
                  )}
                </section>

                {/* Experience & Education Requirements Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {/* Experience */}
                  <section className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800 shadow-lg space-y-2.5">
                    <div className="flex items-center space-x-2 pb-2 border-b border-slate-800">
                      <span className="text-base">⏳</span>
                      <h3 className="text-xs font-bold text-white uppercase tracking-wider">
                        Experience
                      </h3>
                    </div>
                    {expSignals.length > 0 ? (
                      <ul className="space-y-1.5 text-xs text-slate-300">
                        {expSignals.map((exp, idx) => (
                          <li key={idx} className="flex items-start space-x-2">
                            <span className="text-blue-400 mt-0.5">•</span>
                            <span>{exp}</span>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-xs text-slate-500 italic">
                        {isAnalyzed ? "General experience / not specified." : "Pending analysis."}
                      </p>
                    )}
                  </section>

                  {/* Education */}
                  <section className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800 shadow-lg space-y-2.5">
                    <div className="flex items-center space-x-2 pb-2 border-b border-slate-800">
                      <span className="text-base">🎓</span>
                      <h3 className="text-xs font-bold text-white uppercase tracking-wider">
                        Education
                      </h3>
                    </div>
                    {job.education_requirements && job.education_requirements.length > 0 ? (
                      <ul className="space-y-1.5 text-xs text-slate-300">
                        {job.education_requirements.map((edu, idx) => (
                          <li key={idx} className="flex items-start space-x-2">
                            <span className="text-emerald-400 mt-0.5">•</span>
                            <span>{edu}</span>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-xs text-slate-500 italic">
                        {isAnalyzed ? "Degree not explicitly stated." : "Pending analysis."}
                      </p>
                    )}
                  </section>
                </div>

                {/* Responsibilities */}
                {job.responsibilities && job.responsibilities.length > 0 && (
                  <section className="p-6 rounded-2xl bg-slate-900/70 border border-slate-800 shadow-lg space-y-3">
                    <div className="flex items-center space-x-2 pb-2 border-b border-slate-800">
                      <span className="text-base">📋</span>
                      <h2 className="text-sm font-bold text-white">Extracted Key Responsibilities</h2>
                    </div>
                    <ul className="space-y-2 text-xs text-slate-300 leading-relaxed">
                      {job.responsibilities.map((resp, idx) => (
                        <li key={idx} className="flex items-start space-x-2.5">
                          <span className="h-5 w-5 rounded bg-slate-800 text-indigo-400 flex items-center justify-center font-mono text-[10px] font-bold shrink-0 mt-0.5">
                            {idx + 1}
                          </span>
                          <span>{resp}</span>
                        </li>
                      ))}
                    </ul>
                  </section>
                )}

                {/* Raw Job Description Accordion */}
                <details className="p-5 rounded-2xl bg-slate-950/60 border border-slate-800 text-xs text-slate-400 cursor-pointer">
                  <summary className="font-semibold text-slate-300 hover:text-white">
                    View Full Job Description Text
                  </summary>
                  <p className="mt-3 whitespace-pre-wrap font-sans text-slate-300 leading-relaxed pt-3 border-t border-slate-800">
                    {job.description}
                  </p>
                </details>
              </div>

              {/* Right Column: Candidate Resume Selection for Matching */}
              <div className="lg:col-span-5 space-y-6">
                <section className="p-6 sm:p-7 rounded-2xl bg-slate-900/80 border border-indigo-900/60 shadow-xl backdrop-blur space-y-5">
                  <div className="flex items-center space-x-2.5 pb-3 border-b border-slate-800">
                    <span className="text-lg">🎯</span>
                    <div>
                      <h2 className="text-base font-bold text-white tracking-tight">
                        Match With Resume
                      </h2>
                      <p className="text-[11px] text-slate-400">
                        Select a candidate resume version to evaluate semantic compatibility.
                      </p>
                    </div>
                  </div>

                  {resumes.length === 0 ? (
                    <div className="p-6 rounded-xl bg-slate-950/60 border border-dashed border-slate-800 text-center space-y-3">
                      <p className="text-xs text-slate-400">No resumes uploaded yet.</p>
                      <Link
                        href="/resume"
                        className="inline-block px-4 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-xl transition"
                      >
                        Upload Resume →
                      </Link>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {resumes.map((r) => {
                        const isSelected = selectedResumeId === r.id;
                        const isEligible = r.has_analysis;

                        return (
                          <div
                            key={r.id}
                            onClick={() => setSelectedResumeId(r.id)}
                            className={`p-4 rounded-xl border transition cursor-pointer flex flex-col space-y-2 ${
                              isSelected
                                ? "bg-indigo-950/40 border-indigo-500 shadow-md"
                                : "bg-slate-950/60 border-slate-800 hover:border-slate-700"
                            }`}
                          >
                            <div className="flex items-center justify-between">
                              <div className="flex items-center space-x-2">
                                <input
                                  type="radio"
                                  name="resume_selection"
                                  checked={isSelected}
                                  onChange={() => setSelectedResumeId(r.id)}
                                  className="text-indigo-600 focus:ring-indigo-500"
                                />
                                <span className="px-2 py-0.5 rounded-md bg-slate-800 font-mono text-[10px] font-bold text-slate-300 uppercase">
                                  v{r.version_number}
                                </span>
                                {r.is_active && (
                                  <span className="px-2 py-0.5 rounded-md bg-emerald-950 text-emerald-400 border border-emerald-800 text-[10px] font-bold uppercase">
                                    Active
                                  </span>
                                )}
                              </div>

                              {r.has_ats_score && r.ats_score !== null && (
                                <span className="text-[11px] font-bold text-emerald-400">
                                  ATS: {r.ats_score}/100
                                </span>
                              )}
                            </div>

                            <p className="text-xs font-semibold text-white truncate pl-5">
                              {r.original_filename}
                            </p>

                            <div className="pl-5 text-[11px] flex items-center justify-between text-slate-400">
                              <span>
                                {isEligible ? (
                                  <span className="text-emerald-400">✓ Structured Analysis Complete</span>
                                ) : (
                                  <span className="text-amber-400">Analysis Pending</span>
                                )}
                              </span>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}

                  {/* Validation State for selected resume */}
                  {selectedResume && !selectedResume.has_analysis && (
                    <div className="p-4 rounded-xl bg-amber-950/40 border border-amber-800/60 text-amber-300 text-xs space-y-2">
                      <p className="font-medium">
                        ⚠️ This resume needs structured analysis before job matching.
                      </p>
                      <Link
                        href={`/resume/${selectedResume.id}/analysis`}
                        className="inline-block px-3.5 py-1.5 text-xs font-semibold text-white bg-amber-700 hover:bg-amber-600 rounded-lg transition"
                      >
                        Analyze Resume →
                      </Link>
                    </div>
                  )}

                  {/* Run Matching Button */}
                  <button
                    type="button"
                    onClick={handleMatchResume}
                    disabled={!selectedResumeId || !selectedResume?.has_analysis || matchingInProgress}
                    className="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-emerald-600 via-teal-600 to-indigo-600 hover:from-emerald-500 hover:to-indigo-500 text-white font-semibold text-xs shadow-lg shadow-emerald-600/25 transition disabled:opacity-50 flex items-center justify-center space-x-2"
                  >
                    {matchingInProgress ? (
                      <>
                        <div className="animate-spin h-3.5 w-3.5 border-2 border-white border-t-transparent rounded-full" />
                        <span>Running Semantic Matching...</span>
                      </>
                    ) : (
                      <>
                        <span>🎯 Match Resume to Job</span>
                        <span>→</span>
                      </>
                    )}
                  </button>
                </section>
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
