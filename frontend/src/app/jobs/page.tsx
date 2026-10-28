"use client";

import React, { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import {
  createJobApi,
  getJobsApi,
  JobDescriptionResponse,
  JobDescriptionCreate,
  ApiError,
} from "@/lib/api";

export default function JobsWorkspacePage() {
  const router = useRouter();
  const { user, token, loading: authLoading, logout, isAuthenticated } = useAuth();

  const [jobs, setJobs] = useState<JobDescriptionResponse[]>([]);
  const [loadingJobs, setLoadingJobs] = useState<boolean>(true);
  const [errorJobs, setErrorJobs] = useState<string | null>(null);

  // Form State
  const [title, setTitle] = useState<string>("");
  const [company, setCompany] = useState<string>("");
  const [description, setDescription] = useState<string>("");
  const [formSubmitting, setFormSubmitting] = useState<boolean>(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [formSuccess, setFormSuccess] = useState<string | null>(null);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [authLoading, isAuthenticated, router]);

  const loadJobs = useCallback(async (authToken: string) => {
    setLoadingJobs(true);
    setErrorJobs(null);
    try {
      const data = await getJobsApi(authToken);
      setJobs(data);
    } catch (err) {
      if (err instanceof ApiError) {
        setErrorJobs(err.message);
      } else {
        setErrorJobs("We couldn't load your saved jobs. Please try again.");
      }
    } finally {
      setLoadingJobs(false);
    }
  }, []);

  useEffect(() => {
    if (token) {
      loadJobs(token);
    }
  }, [token, loadJobs]);

  const handleCreateJob = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;

    if (!title.trim()) {
      setFormError("Job title is required.");
      return;
    }
    if (!description.trim() || description.trim().length < 10) {
      setFormError("Please provide a meaningful job description (at least 10 characters).");
      return;
    }

    setFormSubmitting(true);
    setFormError(null);
    setFormSuccess(null);

    try {
      const payload: JobDescriptionCreate = {
        title: title.trim(),
        company: company.trim() || undefined,
        description: description.trim(),
      };

      const newJob = await createJobApi(payload, token);
      setFormSuccess(`Job posting "${newJob.title}" added successfully!`);
      setTitle("");
      setCompany("");
      setDescription("");
      await loadJobs(token);
    } catch (err) {
      if (err instanceof ApiError) {
        setFormError(err.message);
      } else {
        setFormError("Failed to save job description. Please check the inputs and try again.");
      }
    } finally {
      setFormSubmitting(false);
    }
  };

  if (authLoading || !user) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-slate-950 text-slate-100">
        <div className="flex flex-col items-center space-y-4">
          <div className="animate-spin h-10 w-10 border-3 border-indigo-500 border-t-transparent rounded-full" />
          <p className="text-sm text-slate-400 font-medium animate-pulse">
            Loading Job Description Workspace...
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
                <span className="ml-2 text-xs uppercase tracking-widest font-semibold px-2 py-0.5 rounded-full bg-indigo-950 text-indigo-400 border border-indigo-800/50">
                  Job Intelligence
                </span>
              </div>
            </Link>
          </div>

          <div className="flex items-center space-x-4">
            <Link
              href="/dashboard"
              className="text-xs px-3.5 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 font-medium transition flex items-center space-x-1.5"
            >
              <span>← Dashboard</span>
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
        {/* Page Title Banner */}
        <div>
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-medium mb-3">
            <span>🎯</span>
            <span>Target Role Intelligence</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Job Description & Resume Matching Workspace
          </h1>
          <p className="text-sm text-slate-400 mt-1 max-w-3xl">
            Save job postings, extract structured technical requirements, and run transparent 4-component semantic matching against your candidate resume versions.
          </p>
        </div>

        {/* 2-Column Layout: Create Form (Left) & Saved Jobs (Right) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Create Job Form (Left Column) */}
          <section className="lg:col-span-5 bg-slate-900/70 border border-slate-800 rounded-2xl p-6 sm:p-7 shadow-xl backdrop-blur space-y-5">
            <div className="flex items-center space-x-2.5 pb-3 border-b border-slate-800">
              <span className="text-lg">📝</span>
              <h2 className="text-base font-bold text-white tracking-tight">
                Add Target Job Description
              </h2>
            </div>

            {formError && (
              <div className="p-3.5 rounded-xl bg-rose-950/40 border border-rose-800/60 text-rose-300 text-xs flex items-center space-x-2">
                <span>⚠️</span>
                <span>{formError}</span>
              </div>
            )}

            {formSuccess && (
              <div className="p-3.5 rounded-xl bg-emerald-950/40 border border-emerald-800/60 text-emerald-300 text-xs flex items-center space-x-2">
                <span>✓</span>
                <span>{formSuccess}</span>
              </div>
            )}

            <form onSubmit={handleCreateJob} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-300 font-semibold mb-1.5">
                  Job Title <span className="text-rose-400">*</span>
                </label>
                <input
                  type="text"
                  placeholder="e.g. Senior Backend Engineer"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 focus:border-indigo-500 focus:outline-none text-white text-xs transition"
                  disabled={formSubmitting}
                />
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1.5">
                  Company / Organization <span className="text-slate-500 font-normal">(Optional)</span>
                </label>
                <input
                  type="text"
                  placeholder="e.g. Acme Cloud Corp"
                  value={company}
                  onChange={(e) => setCompany(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 focus:border-indigo-500 focus:outline-none text-white text-xs transition"
                  disabled={formSubmitting}
                />
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1.5">
                  Job Description Text <span className="text-rose-400">*</span>
                </label>
                <textarea
                  rows={8}
                  placeholder="Paste the full job description including responsibilities, required skills, and qualifications here..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 focus:border-indigo-500 focus:outline-none text-white text-xs transition leading-relaxed"
                  disabled={formSubmitting}
                />
              </div>

              <button
                type="submit"
                disabled={formSubmitting}
                className="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-semibold text-xs shadow-lg shadow-indigo-600/25 transition disabled:opacity-50 flex items-center justify-center space-x-2"
              >
                {formSubmitting ? (
                  <>
                    <div className="animate-spin h-3.5 w-3.5 border-2 border-white border-t-transparent rounded-full" />
                    <span>Saving Job Posting...</span>
                  </>
                ) : (
                  <>
                    <span>Add Job Description</span>
                    <span>→</span>
                  </>
                )}
              </button>
            </form>
          </section>

          {/* Saved Jobs List (Right Column) */}
          <section className="lg:col-span-7 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2.5">
                <span className="text-lg">💼</span>
                <h2 className="text-base font-bold text-white tracking-tight">
                  Saved Job Descriptions
                </h2>
                {jobs.length > 0 && (
                  <span className="px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 text-[10px] font-bold">
                    {jobs.length} {jobs.length === 1 ? "posting" : "postings"}
                  </span>
                )}
              </div>
            </div>

            {loadingJobs ? (
              <div className="p-8 rounded-2xl bg-slate-900/50 border border-slate-800 flex items-center justify-center space-x-3">
                <div className="animate-spin h-5 w-5 border-2 border-indigo-500 border-t-transparent rounded-full" />
                <span className="text-xs text-slate-400">Loading saved jobs...</span>
              </div>
            ) : errorJobs ? (
              <div className="p-6 rounded-2xl bg-rose-950/30 border border-rose-800/50 text-rose-300 flex items-center justify-between text-xs">
                <span>{errorJobs}</span>
                <button
                  onClick={() => token && loadJobs(token)}
                  className="px-3 py-1.5 bg-rose-700 hover:bg-rose-600 rounded-lg text-white font-semibold transition"
                >
                  Retry
                </button>
              </div>
            ) : jobs.length === 0 ? (
              <div className="p-8 rounded-2xl bg-slate-900/40 border border-dashed border-slate-800 text-center space-y-3">
                <div className="h-12 w-12 rounded-2xl bg-blue-600/10 border border-blue-500/20 flex items-center justify-center text-2xl mx-auto text-blue-400">
                  📋
                </div>
                <h3 className="text-sm font-bold text-white">No job descriptions yet</h3>
                <p className="text-xs text-slate-400 max-w-sm mx-auto">
                  Add a job description to start extracting requirements and matching your candidate resume.
                </p>
              </div>
            ) : (
              <div className="space-y-3.5">
                {jobs.map((job) => {
                  const isAnalyzed = Boolean(job.extracted_skills && job.extracted_skills.length > 0);
                  return (
                    <div
                      key={job.id}
                      className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 hover:border-slate-700 transition shadow-lg space-y-3"
                    >
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                        <div>
                          <h3 className="text-sm sm:text-base font-bold text-white">
                            {job.title}
                          </h3>
                          <p className="text-xs text-slate-400 mt-0.5 flex items-center space-x-2">
                            {job.company && <span className="text-indigo-300 font-medium">{job.company}</span>}
                            {job.company && <span>•</span>}
                            <span>
                              Saved on{" "}
                              {new Date(job.created_at).toLocaleDateString("en-US", {
                                month: "short",
                                day: "numeric",
                                year: "numeric",
                              })}
                            </span>
                          </p>
                        </div>

                        {/* Status Badge */}
                        <div>
                          {isAnalyzed ? (
                            <span className="px-2.5 py-1 rounded-lg bg-emerald-950/80 border border-emerald-800/80 text-emerald-300 text-[10px] font-bold uppercase tracking-wider flex items-center space-x-1">
                              <span>✓</span>
                              <span>Requirements Analyzed</span>
                            </span>
                          ) : (
                            <span className="px-2.5 py-1 rounded-lg bg-amber-950/60 border border-amber-800/60 text-amber-300 text-[10px] font-bold uppercase tracking-wider">
                              Not Analyzed
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Snippet */}
                      <p className="text-xs text-slate-300 line-clamp-2 leading-relaxed">
                        {job.description}
                      </p>

                      {/* Skills Preview if Analyzed */}
                      {isAnalyzed && job.extracted_skills && (
                        <div className="flex flex-wrap gap-1.5 pt-1">
                          {job.extracted_skills.slice(0, 6).map((skill, idx) => (
                            <span
                              key={idx}
                              className="px-2 py-0.5 rounded-md bg-slate-950 border border-slate-800 text-[10px] text-slate-300 font-mono"
                            >
                              {skill}
                            </span>
                          ))}
                          {job.extracted_skills.length > 6 && (
                            <span className="px-2 py-0.5 rounded-md bg-slate-950 text-[10px] text-slate-500 font-mono">
                              +{job.extracted_skills.length - 6} more
                            </span>
                          )}
                        </div>
                      )}

                      {/* Action Links */}
                      <div className="flex items-center justify-end space-x-2.5 pt-2 border-t border-slate-800/60">
                        <Link
                          href={`/jobs/${job.id}`}
                          className="px-3.5 py-1.5 text-xs font-semibold text-slate-300 hover:text-white bg-slate-950 hover:bg-slate-800 border border-slate-800 rounded-xl transition"
                        >
                          View Requirements
                        </Link>
                        <Link
                          href={`/jobs/${job.id}`}
                          className="px-4 py-1.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-xl transition shadow-md shadow-indigo-600/20 flex items-center space-x-1"
                        >
                          <span>Match Resume</span>
                          <span>→</span>
                        </Link>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </section>
        </div>
      </main>
    </div>
  );
}
