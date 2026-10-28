"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";

interface HealthData {
  status: string;
  message: string;
  service?: string;
  version?: string;
}

export default function Home() {
  const { user, isAuthenticated, loading: authLoading } = useAuth();
  const [healthStatus, setHealthStatus] = useState<HealthData | null>(null);
  const [loadingHealth, setLoadingHealth] = useState(false);
  const [errorHealth, setErrorHealth] = useState<string | null>(null);

  const checkHealth = async () => {
    setLoadingHealth(true);
    setErrorHealth(null);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${apiUrl}/api/health`);
      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }
      const data = await res.json();
      setHealthStatus(data);
    } catch (err: unknown) {
      setErrorHealth(
        err instanceof Error ? err.message : "Failed to connect to backend service"
      );
      setHealthStatus(null);
    } finally {
      setLoadingHealth(false);
    }
  };

  useEffect(() => {
    checkHealth();
  }, []);

  return (
    <div className="min-h-screen flex flex-col bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 text-slate-100">
      {/* Navigation Header */}
      <header className="border-b border-slate-800/80 backdrop-blur sticky top-0 z-50 bg-slate-950/70">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center text-white font-bold shadow-lg shadow-indigo-500/20">
              CP
            </div>
            <div>
              <span className="text-lg font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-indigo-300 to-purple-400">
                CareerPilot AI
              </span>
              <span className="ml-2 text-xs uppercase tracking-widest font-semibold px-2 py-0.5 rounded-full bg-indigo-950 text-indigo-400 border border-indigo-800/50">
                Career Platform
              </span>
            </div>
          </div>
          
          <div className="flex items-center space-x-3 sm:space-x-4">
            {/* Backend connection pill */}
            <div className="hidden sm:flex items-center space-x-2 text-xs text-slate-400 bg-slate-900 border border-slate-800 rounded-full px-3 py-1.5">
              <span
                className={`h-2 w-2 rounded-full ${
                  healthStatus?.status === "success"
                    ? "bg-emerald-400 shadow-sm shadow-emerald-400 animate-pulse"
                    : errorHealth
                    ? "bg-amber-400"
                    : "bg-slate-500"
                }`}
              />
              <span>
                {loadingHealth
                  ? "Checking Backend..."
                  : healthStatus?.status === "success"
                  ? "Backend Connected"
                  : errorHealth
                  ? "Backend Standby"
                  : "Status Idle"}
              </span>
            </div>

            {/* Auth Buttons */}
            {!authLoading && (
              <>
                {isAuthenticated && user ? (
                  <Link
                    href="/dashboard"
                    className="inline-flex items-center space-x-2 text-xs font-semibold px-3.5 py-1.5 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white shadow-md shadow-indigo-500/20 transition"
                  >
                    <span>Dashboard ({user.name.split(" ")[0]})</span>
                    <span>→</span>
                  </Link>
                ) : (
                  <div className="flex items-center space-x-2">
                    <Link
                      href="/login"
                      className="text-xs font-medium px-3 py-1.5 rounded-lg text-slate-300 hover:text-white hover:bg-slate-800/80 transition"
                    >
                      Sign In
                    </Link>
                    <Link
                      href="/register"
                      className="text-xs font-semibold px-3.5 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white shadow-md shadow-indigo-600/20 transition"
                    >
                      Register
                    </Link>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 flex flex-col justify-between">
        {/* Hero Section */}
        <section className="text-center py-10 max-w-3xl mx-auto">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-medium mb-6">
            <span>✨</span>
            <span>Next-Generation Recruitment Preparation Platform</span>
          </div>
          <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-white mb-6 leading-tight">
            Navigate Your Career with{" "}
            <span className="bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-indigo-300 to-purple-400">
              Autonomous Intelligence
            </span>
          </h1>
          <p className="text-base sm:text-lg text-slate-400 mb-8 leading-relaxed">
            Prepare, optimize, and excel in your recruitment journey. Secure candidate authentication is now live.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-10">
            {isAuthenticated ? (
              <Link
                href="/dashboard"
                className="w-full sm:w-auto px-6 py-3 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-semibold shadow-lg shadow-indigo-600/30 transition text-sm"
              >
                Go to Candidate Dashboard →
              </Link>
            ) : (
              <>
                <Link
                  href="/register"
                  className="w-full sm:w-auto px-6 py-3 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-semibold shadow-lg shadow-indigo-600/30 transition text-sm"
                >
                  Create Free Account →
                </Link>
                <Link
                  href="/login"
                  className="w-full sm:w-auto px-6 py-3 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white border border-slate-800 font-semibold transition text-sm"
                >
                  Sign In to Account
                </Link>
              </>
            )}
          </div>

          {/* Quick Backend Verification Widget */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 text-left shadow-xl shadow-black/40 backdrop-blur">
            <div className="flex items-center justify-between mb-4 border-b border-slate-800 pb-3">
              <div className="flex items-center space-x-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Backend Health & Auth API Verification
                </span>
                <code className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-indigo-300">
                  GET /api/health
                </code>
              </div>
              <button
                onClick={checkHealth}
                disabled={loadingHealth}
                className="text-xs px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium transition cursor-pointer"
              >
                {loadingHealth ? "Checking..." : "Re-check Health"}
              </button>
            </div>

            {loadingHealth && (
              <p className="text-sm text-slate-400 animate-pulse font-mono">
                Querying FastAPI endpoint...
              </p>
            )}

            {healthStatus && (
              <div className="bg-slate-950 rounded-xl p-4 border border-emerald-900/40">
                <div className="flex items-center space-x-2 mb-2">
                  <span className="text-xs font-bold text-emerald-400 uppercase tracking-wider">
                    ● Connection Success (200 OK)
                  </span>
                </div>
                <pre className="text-xs text-emerald-300/90 font-mono overflow-x-auto">
                  {JSON.stringify(healthStatus, null, 2)}
                </pre>
              </div>
            )}

            {errorHealth && (
              <div className="bg-slate-950 rounded-xl p-4 border border-amber-900/40">
                <p className="text-xs text-amber-400 font-medium mb-1">
                  Backend offline or unreachable at standard port:
                </p>
                <p className="text-xs text-slate-400 font-mono">
                  {errorHealth} (Start backend via `uvicorn app.main:app --reload`)
                </p>
              </div>
            )}
          </div>
        </section>

        {/* Feature Modules Placeholder Grid */}
        <section className="py-10">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-400 mb-6 text-center">
            Upcoming Modular Roadmap
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="p-6 rounded-2xl bg-slate-900/50 border border-slate-800 hover:border-slate-700 transition">
              <div className="h-10 w-10 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400 text-lg mb-4">
                📄
              </div>
              <h3 className="text-base font-semibold text-white mb-2">ATS Resume Optimization</h3>
              <p className="text-sm text-slate-400 leading-relaxed">
                Deterministic PyMuPDF parsing, structured skill extraction, and transparent weighted ATS scoring.
              </p>
              <div className="mt-4 inline-block text-xs text-emerald-400 font-semibold bg-emerald-950/60 border border-emerald-800/60 px-2.5 py-1 rounded-md">
                ✓ Live Feature
              </div>
            </div>

            <div className="p-6 rounded-2xl bg-slate-900/50 border border-slate-800 hover:border-slate-700 transition">
              <div className="h-10 w-10 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400 text-lg mb-4">
                🎙️
              </div>
              <h3 className="text-base font-semibold text-white mb-2">Technical Interview Practice</h3>
              <p className="text-sm text-slate-400 leading-relaxed">
                Resume-aware adaptive technical interview powered by Google Gemini with instant answer evaluation and scoring.
              </p>
              <div className="mt-4 inline-block text-xs text-emerald-400 font-semibold bg-emerald-950/60 border border-emerald-800/60 px-2.5 py-1 rounded-md">
                ✓ Live Feature
              </div>
            </div>

            <div className="p-6 rounded-2xl bg-slate-900/50 border border-slate-800 hover:border-slate-700 transition">
              <div className="h-10 w-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 text-lg mb-4">
                🎯
              </div>
              <h3 className="text-base font-semibold text-white mb-2">Smart Job Matching</h3>
              <p className="text-sm text-slate-400 leading-relaxed">
                Deterministic 4-component resume-to-job matching, prioritized skill gaps, and role improvement insights.
              </p>
              <div className="mt-4 inline-block text-xs text-emerald-400 font-semibold bg-emerald-950/60 border border-emerald-800/60 px-2.5 py-1 rounded-md">
                ✓ Live Feature
              </div>
            </div>
          </div>
        </section>

        {/* Monorepo Architecture Stack Status */}
        <footer className="border-t border-slate-800/80 pt-8 pb-4 text-center text-xs text-slate-500">
          <div className="flex flex-wrap justify-center gap-6 mb-4 font-mono">
            <span>Frontend: Next.js + TS + Tailwind</span>
            <span>•</span>
            <span>Backend: FastAPI + JWT Auth</span>
            <span>•</span>
            <span>Database: PostgreSQL</span>
          </div>
          <p>© {new Date().getFullYear()} CareerPilot AI. All rights reserved.</p>
        </footer>
      </main>
    </div>
  );
}
