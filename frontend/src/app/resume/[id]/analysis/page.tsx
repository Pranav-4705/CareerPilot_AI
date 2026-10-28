"use client";

import React, { useEffect, useState, use } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import {
  analyzeResumeApi,
  getResumeApi,
  ResumeAnalysisResponse,
  ResumeDetailResponse,
  ApiError,
} from "@/lib/api";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function ResumeAnalysisPage({ params }: PageProps) {
  const resolvedParams = use(params);
  const resumeId = Number(resolvedParams.id);
  const router = useRouter();
  const { token, loading: authLoading, logout, isAuthenticated } = useAuth();

  const [resume, setResume] = useState<ResumeDetailResponse | null>(null);
  const [analysis, setAnalysis] = useState<ResumeAnalysisResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [skillSearch, setSkillSearch] = useState<string>("");
  const [expandedRawText, setExpandedRawText] = useState<{ [key: string]: boolean }>({});

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [authLoading, isAuthenticated, router]);

  const loadData = React.useCallback(async (authToken: string) => {
    if (!resumeId || isNaN(resumeId)) {
      setError("Invalid Resume ID provided in URL.");
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // 1. Fetch resume details
      const resumeData = await getResumeApi(resumeId, authToken);
      setResume(resumeData);

      // 2. Perform/Fetch structured analysis
      const analysisData = await analyzeResumeApi(resumeId, authToken);
      setAnalysis(analysisData);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Failed to load structured resume analysis. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  }, [resumeId]);

  useEffect(() => {
    if (token) {
      loadData(token);
    }
  }, [token, loadData]);

  const toggleRawText = (key: string) => {
    setExpandedRawText((prev) => ({
      ...prev,
      [key]: !prev[key],
    }));
  };

  const filteredSkills = (analysis?.extracted_skills || []).filter((s) =>
    s.toLowerCase().includes(skillSearch.toLowerCase())
  );

  if (authLoading || (loading && !analysis)) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-slate-950 text-slate-100">
        <div className="flex flex-col items-center space-y-4">
          <div className="animate-spin h-10 w-10 border-3 border-indigo-500 border-t-transparent rounded-full" />
          <p className="text-sm text-slate-400 font-medium animate-pulse">
            Analyzing resume structure and extracting entities...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 text-slate-100">
      {/* Navigation Header */}
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
                <span className="ml-2 text-xs uppercase tracking-widest font-semibold px-2 py-0.5 rounded-full bg-purple-950 text-purple-400 border border-purple-800/50">
                  Analysis
                </span>
              </div>
            </Link>
          </div>

          <div className="flex items-center space-x-3">
            <Link
              href="/resume"
              className="text-xs px-3 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 font-medium transition"
            >
              + Upload Resume
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

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full">
        {/* Breadcrumb Navigation */}
        <nav className="flex items-center space-x-2 text-xs text-slate-400 mb-6">
          <Link href="/dashboard" className="hover:text-indigo-400 transition">Dashboard</Link>
          <span>/</span>
          <Link href="/resume" className="hover:text-indigo-400 transition">Resume</Link>
          <span>/</span>
          <span className="text-slate-200 font-semibold font-mono">#{resumeId} Analysis</span>
        </nav>

        {/* Error Alert */}
        {error && (
          <div className="mb-8 p-6 rounded-2xl bg-rose-950/40 border border-rose-800/60 text-rose-300 shadow-xl">
            <div className="flex items-start space-x-3">
              <span className="text-rose-400 text-xl">❌</span>
              <div className="flex-1">
                <h3 className="text-base font-bold text-rose-200">Analysis Error</h3>
                <p className="text-xs sm:text-sm mt-1">{error}</p>
                <div className="mt-4 flex space-x-3">
                  <button
                    onClick={() => token && loadData(token)}
                    className="px-4 py-1.5 text-xs font-semibold text-white bg-rose-700 hover:bg-rose-600 rounded-xl transition"
                  >
                    Retry Analysis
                  </button>
                  <Link
                    href="/resume"
                    className="px-4 py-1.5 text-xs font-semibold text-slate-300 bg-slate-900 hover:bg-slate-800 border border-slate-800 rounded-xl transition"
                  >
                    Back to Upload
                  </Link>
                </div>
              </div>
            </div>
          </div>
        )}

        {analysis && (
          <div className="space-y-8">
            {/* Top Overview Banner */}
            <div className="p-6 sm:p-8 rounded-2xl bg-slate-900/70 border border-slate-800 shadow-xl backdrop-blur relative overflow-hidden">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 relative z-10">
                <div>
                  <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-medium mb-3">
                    <span>✓</span>
                    <span>Deterministic Extraction Complete</span>
                  </div>
                  <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
                    Structured Resume Analysis
                  </h1>
                  <p className="text-xs sm:text-sm text-slate-400 mt-1 flex items-center space-x-2">
                    <span className="font-medium text-slate-300 font-mono">
                      {resume?.original_filename || "Candidate Resume"}
                    </span>
                    <span>•</span>
                    <span>Document ID #{analysis.resume_id}</span>
                  </p>
                </div>

                <div className="flex flex-wrap items-center gap-3 shrink-0">
                  <button
                    onClick={() => token && loadData(token)}
                    disabled={loading}
                    className="px-3.5 py-2 text-xs font-semibold text-slate-300 bg-slate-800/80 hover:bg-slate-700 border border-slate-700 rounded-xl transition disabled:opacity-50 flex items-center space-x-1.5"
                  >
                    <span>🔄</span>
                    <span>Re-Analyze</span>
                  </button>

                  <Link
                    href={`/resume/${resumeId}/ats`}
                    className="px-5 py-2 text-xs font-semibold text-white bg-gradient-to-r from-emerald-600 via-teal-600 to-blue-600 hover:from-emerald-500 hover:to-blue-500 rounded-xl transition shadow-lg shadow-emerald-600/25 flex items-center space-x-2"
                  >
                    <span>🎯 Run ATS Analysis</span>
                    <span>→</span>
                  </Link>
                </div>
              </div>

              {/* Stat Pills */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-6 pt-6 border-t border-slate-800/80">
                <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/60">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">Skills Extracted</span>
                  <span className="text-xl font-extrabold text-indigo-400">{analysis.extracted_skills?.length || 0}</span>
                </div>
                <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/60">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">Experience Roles</span>
                  <span className="text-xl font-extrabold text-blue-400">{analysis.experience?.length || 0}</span>
                </div>
                <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/60">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">Education Entries</span>
                  <span className="text-xl font-extrabold text-emerald-400">{analysis.education?.length || 0}</span>
                </div>
                <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/60">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">Projects & Certs</span>
                  <span className="text-xl font-extrabold text-purple-400">
                    {(analysis.projects?.length || 0) + (analysis.certifications?.length || 0)}
                  </span>
                </div>
              </div>
            </div>

            {/* Section 1: Extracted Technical Skills */}
            <section className="p-6 sm:p-8 rounded-2xl bg-slate-900/70 border border-slate-800 shadow-xl backdrop-blur">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6 pb-4 border-b border-slate-800">
                <div className="flex items-center space-x-3">
                  <div className="h-9 w-9 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 text-lg">
                    ⚡
                  </div>
                  <div>
                    <h2 className="text-lg font-bold text-white">Extracted Technical Skills</h2>
                    <p className="text-xs text-slate-400">
                      Standardized technologies, languages, and frameworks identified across your document.
                    </p>
                  </div>
                </div>

                {analysis.extracted_skills?.length > 0 && (
                  <div className="w-full sm:w-64">
                    <input
                      type="text"
                      placeholder="Filter extracted skills..."
                      value={skillSearch}
                      onChange={(e) => setSkillSearch(e.target.value)}
                      className="w-full px-3 py-1.5 text-xs bg-slate-950 border border-slate-800 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition"
                    />
                  </div>
                )}
              </div>

              {analysis.extracted_skills && analysis.extracted_skills.length > 0 ? (
                <div>
                  <div className="flex flex-wrap gap-2">
                    {filteredSkills.map((skill, index) => (
                      <span
                        key={index}
                        className="px-3 py-1.5 rounded-xl bg-gradient-to-r from-indigo-950/70 to-blue-950/70 border border-indigo-800/60 text-indigo-200 text-xs font-semibold shadow-sm hover:border-indigo-500 transition-colors"
                      >
                        {skill}
                      </span>
                    ))}
                  </div>
                  {filteredSkills.length === 0 && (
                    <p className="text-xs text-slate-500 italic mt-2">
                      No skills match &quot;{skillSearch}&quot;.
                    </p>
                  )}
                </div>
              ) : (
                <div className="p-6 rounded-xl bg-slate-950/60 border border-dashed border-slate-800 text-center">
                  <p className="text-xs text-slate-400">
                    No explicit technical skills detected in the document against the standard taxonomy.
                  </p>
                </div>
              )}
            </section>

            {/* Section 2: Work Experience */}
            <section className="p-6 sm:p-8 rounded-2xl bg-slate-900/70 border border-slate-800 shadow-xl backdrop-blur">
              <div className="flex items-center space-x-3 mb-6 pb-4 border-b border-slate-800">
                <div className="h-9 w-9 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400 text-lg">
                  💼
                </div>
                <div>
                  <h2 className="text-lg font-bold text-white">Work Experience</h2>
                  <p className="text-xs text-slate-400">
                    Extracted professional roles, companies, and achievement details.
                  </p>
                </div>
              </div>

              {analysis.experience && analysis.experience.length > 0 ? (
                <div className="space-y-4">
                  {analysis.experience.map((item, idx) => {
                    const itemKey = `exp-${idx}`;
                    const isExpanded = expandedRawText[itemKey];
                    return (
                      <div
                        key={idx}
                        className="p-5 rounded-xl bg-slate-950/80 border border-slate-800 hover:border-blue-900/40 transition shadow-sm"
                      >
                        <div className="flex items-start justify-between gap-4">
                          <h3 className="text-sm font-bold text-white leading-snug">
                            {item.title}
                          </h3>
                          <button
                            type="button"
                            onClick={() => toggleRawText(itemKey)}
                            className="text-[11px] text-slate-500 hover:text-indigo-400 transition shrink-0"
                          >
                            {isExpanded ? "Hide Raw Text" : "View Raw"}
                          </button>
                        </div>

                        {item.details && item.details.length > 0 ? (
                          <ul className="mt-3 space-y-2 text-xs text-slate-300 list-disc list-inside">
                            {item.details.map((detail, dIdx) => (
                              <li key={dIdx} className="leading-relaxed pl-1">
                                <span>{detail.replace(/^[\-\•\*\s]+/, "")}</span>
                              </li>
                            ))}
                          </ul>
                        ) : null}

                        {isExpanded && (
                          <div className="mt-3 p-3 rounded-lg bg-slate-900 border border-slate-800 text-[11px] font-mono text-slate-400 whitespace-pre-wrap">
                            {item.raw_text}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="p-6 rounded-xl bg-slate-950/60 border border-dashed border-slate-800 text-center">
                  <p className="text-xs text-slate-400">
                    No work experience section identified in this document.
                  </p>
                </div>
              )}
            </section>

            {/* Section 3: Education */}
            <section className="p-6 sm:p-8 rounded-2xl bg-slate-900/70 border border-slate-800 shadow-xl backdrop-blur">
              <div className="flex items-center space-x-3 mb-6 pb-4 border-b border-slate-800">
                <div className="h-9 w-9 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 text-lg">
                  🎓
                </div>
                <div>
                  <h2 className="text-lg font-bold text-white">Education & Academics</h2>
                  <p className="text-xs text-slate-400">
                    Extracted degrees, academic institutions, and certifications.
                  </p>
                </div>
              </div>

              {analysis.education && analysis.education.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {analysis.education.map((item, idx) => (
                    <div
                      key={idx}
                      className="p-5 rounded-xl bg-slate-950/80 border border-slate-800 hover:border-emerald-900/40 transition shadow-sm"
                    >
                      <h3 className="text-sm font-bold text-emerald-300 mb-1">
                        {item.title}
                      </h3>
                      {item.details && item.details.length > 0 && (
                        <div className="space-y-1 mt-2 text-xs text-slate-300">
                          {item.details.map((d, dIdx) => (
                            <p key={dIdx} className="leading-relaxed text-slate-400">
                              {d}
                            </p>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-6 rounded-xl bg-slate-950/60 border border-dashed border-slate-800 text-center">
                  <p className="text-xs text-slate-400">
                    No formal education section was detected in this document.
                  </p>
                </div>
              )}
            </section>

            {/* Section 4: Projects & Certifications (2-Column Grid) */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              {/* Projects */}
              <section className="p-6 sm:p-8 rounded-2xl bg-slate-900/70 border border-slate-800 shadow-xl backdrop-blur flex flex-col justify-between">
                <div>
                  <div className="flex items-center space-x-3 mb-6 pb-4 border-b border-slate-800">
                    <div className="h-9 w-9 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400 text-lg">
                      🚀
                    </div>
                    <div>
                      <h2 className="text-base font-bold text-white">Technical Projects</h2>
                      <p className="text-xs text-slate-400">Applied engineering projects and platforms.</p>
                    </div>
                  </div>

                  {analysis.projects && analysis.projects.length > 0 ? (
                    <div className="space-y-4">
                      {analysis.projects.map((item, idx) => (
                        <div
                          key={idx}
                          className="p-4 rounded-xl bg-slate-950/80 border border-slate-800/80"
                        >
                          <h3 className="text-xs font-bold text-purple-300 mb-1.5">
                            {item.title}
                          </h3>
                          {item.details && item.details.length > 0 && (
                            <ul className="space-y-1 text-xs text-slate-300 list-disc list-inside">
                              {item.details.map((d, dIdx) => (
                                <li key={dIdx} className="leading-relaxed">
                                  <span>{d.replace(/^[\-\•\*\s]+/, "")}</span>
                                </li>
                              ))}
                            </ul>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="p-6 rounded-xl bg-slate-950/60 border border-dashed border-slate-800 text-center">
                      <p className="text-xs text-slate-400">
                        No dedicated projects section identified.
                      </p>
                    </div>
                  )}
                </div>
              </section>

              {/* Certifications */}
              <section className="p-6 sm:p-8 rounded-2xl bg-slate-900/70 border border-slate-800 shadow-xl backdrop-blur flex flex-col justify-between">
                <div>
                  <div className="flex items-center space-x-3 mb-6 pb-4 border-b border-slate-800">
                    <div className="h-9 w-9 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400 text-lg">
                      🏆
                    </div>
                    <div>
                      <h2 className="text-base font-bold text-white">Certifications & Licenses</h2>
                      <p className="text-xs text-slate-400">Recognized industry credentials and qualifications.</p>
                    </div>
                  </div>

                  {analysis.certifications && analysis.certifications.length > 0 ? (
                    <div className="space-y-3">
                      {analysis.certifications.map((item, idx) => (
                        <div
                          key={idx}
                          className="p-4 rounded-xl bg-slate-950/80 border border-slate-800/80 flex items-start space-x-3"
                        >
                          <span className="text-amber-400 text-sm">🎖️</span>
                          <div>
                            <h3 className="text-xs font-bold text-white">
                              {item.title}
                            </h3>
                            {item.details && item.details.length > 0 && (
                              <p className="text-[11px] text-slate-400 mt-1">
                                {item.details.join(" • ")}
                              </p>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="p-6 rounded-xl bg-slate-950/60 border border-dashed border-slate-800 text-center">
                      <p className="text-xs text-slate-400">
                        No certifications section identified in this document.
                      </p>
                    </div>
                  )}
                </div>
              </section>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
