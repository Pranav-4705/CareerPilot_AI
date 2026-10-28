"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import {
  uploadResumeApi,
  parseResumeApi,
  ResumeUploadResponse,
  ResumeParseResponse,
  ApiError,
} from "@/lib/api";

const MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024; // 5 MB
const ALLOWED_EXTENSIONS = [".pdf", ".docx"];

export default function ResumeUploadPage() {
  const router = useRouter();
  const { user, token, loading, logout, isAuthenticated } = useAuth();

  // File state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  // Upload state
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadSuccess, setUploadSuccess] = useState<ResumeUploadResponse | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  // Parse state
  const [isParsing, setIsParsing] = useState<boolean>(false);
  const [parseSuccess, setParseSuccess] = useState<ResumeParseResponse | null>(null);
  const [parseError, setParseError] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Enforce authentication
  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.push("/login");
    }
  }, [loading, isAuthenticated, router]);

  const validateAndSetFile = useCallback((file: File) => {
    setValidationError(null);
    setUploadError(null);
    setUploadSuccess(null);
    setParseSuccess(null);
    setParseError(null);

    const fileName = file.name.toLowerCase();
    const hasValidExtension = ALLOWED_EXTENSIONS.some((ext) => fileName.endsWith(ext));

    if (!hasValidExtension) {
      setValidationError("Unsupported file format. Please upload a PDF (.pdf) or Word document (.docx).");
      setSelectedFile(null);
      return;
    }

    if (file.size > MAX_FILE_SIZE_BYTES) {
      const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
      setValidationError(`File size (${sizeMB} MB) exceeds the maximum allowed limit of 5 MB.`);
      setSelectedFile(null);
      return;
    }

    if (file.size === 0) {
      setValidationError("The selected file is empty. Please select a valid document.");
      setSelectedFile(null);
      return;
    }

    setSelectedFile(file);
  }, []);

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      validateAndSetFile(file);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      validateAndSetFile(file);
    }
  };

  const handleClearSelectedFile = () => {
    setSelectedFile(null);
    setValidationError(null);
    setUploadError(null);
    setUploadSuccess(null);
    setParseSuccess(null);
    setParseError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleUpload = async () => {
    if (!selectedFile || !token) return;

    setIsUploading(true);
    setUploadError(null);
    setUploadSuccess(null);

    try {
      const res = await uploadResumeApi(selectedFile, token);
      setUploadSuccess(res);
    } catch (err) {
      if (err instanceof ApiError) {
        setUploadError(err.message);
      } else {
        setUploadError("Failed to upload resume. Please check your network connection and try again.");
      }
    } finally {
      setIsUploading(false);
    }
  };

  const handleParse = async () => {
    if (!uploadSuccess || !token) return;

    setIsParsing(true);
    setParseError(null);
    setParseSuccess(null);

    try {
      const res = await parseResumeApi(uploadSuccess.id, token);
      setParseSuccess(res);
    } catch (err) {
      if (err instanceof ApiError) {
        setParseError(err.message);
      } else {
        setParseError("Failed to parse resume text. Please try again.");
      }
    } finally {
      setIsParsing(false);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  if (loading || !user) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-slate-950 text-slate-100">
        <div className="flex flex-col items-center space-y-4">
          <div className="animate-spin h-10 w-10 border-3 border-indigo-500 border-t-transparent rounded-full" />
          <p className="text-sm text-slate-400 font-medium animate-pulse">
            Loading CareerPilot AI Resume Workspace...
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
                <span className="ml-2 text-xs uppercase tracking-widest font-semibold px-2 py-0.5 rounded-full bg-blue-950 text-blue-400 border border-blue-800/50">
                  Resume
                </span>
              </div>
            </Link>
          </div>

          <div className="flex items-center space-x-4">
            <Link
              href="/dashboard"
              className="text-xs px-3.5 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 font-medium transition flex items-center space-x-1.5"
            >
              <span>← Back to Dashboard</span>
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
      <main className="flex-1 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-10 w-full">
        {/* Page Title Banner */}
        <div className="mb-6">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-medium mb-3">
            <span>📄</span>
            <span>Resume Processing Pipeline</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Upload & Process Candidate Resume
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Upload your resume in PDF or DOCX format for text extraction, structure parsing, and downstream ATS matching.
          </p>
        </div>

        {/* Pipeline Stepper */}
        <div className="mb-8 p-4 rounded-2xl bg-slate-900/60 border border-slate-800 flex items-center justify-between overflow-x-auto text-xs font-semibold">
          <div className={`flex items-center space-x-2 ${uploadSuccess ? "text-emerald-400" : "text-indigo-400"}`}>
            <span className={`h-6 w-6 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${uploadSuccess ? "bg-emerald-950 border border-emerald-700" : "bg-indigo-600 text-white"}`}>
              {uploadSuccess ? "✓" : "1"}
            </span>
            <span>1. Upload</span>
          </div>
          <span className="text-slate-600">→</span>
          <div className={`flex items-center space-x-2 ${parseSuccess ? "text-emerald-400" : uploadSuccess ? "text-indigo-400" : "text-slate-500"}`}>
            <span className={`h-6 w-6 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${parseSuccess ? "bg-emerald-950 border border-emerald-700" : uploadSuccess ? "bg-indigo-600 text-white" : "bg-slate-800 text-slate-500"}`}>
              {parseSuccess ? "✓" : "2"}
            </span>
            <span>2. Parse Text</span>
          </div>
          <span className="text-slate-600">→</span>
          <div className="flex items-center space-x-2 text-slate-500">
            <span className="h-6 w-6 rounded-full bg-slate-800 text-slate-500 flex items-center justify-center text-xs font-bold shrink-0">
              3
            </span>
            <span>3. Structure</span>
          </div>
          <span className="text-slate-600">→</span>
          <div className="flex items-center space-x-2 text-slate-500">
            <span className="h-6 w-6 rounded-full bg-slate-800 text-slate-500 flex items-center justify-center text-xs font-bold shrink-0">
              4
            </span>
            <span>4. ATS Scoring</span>
          </div>
        </div>

        {/* Upload Card */}
        <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-6 sm:p-8 shadow-xl relative backdrop-blur mb-8">
          {/* Validation Error Alert */}
          {validationError && (
            <div className="mb-6 p-4 rounded-xl bg-rose-950/40 border border-rose-800/60 text-rose-300 text-xs sm:text-sm flex items-start space-x-3">
              <span className="text-rose-400 text-base">⚠️</span>
              <div>
                <strong className="font-semibold block mb-0.5">Invalid File:</strong>
                <span>{validationError}</span>
              </div>
            </div>
          )}

          {/* Upload Error Alert */}
          {uploadError && (
            <div className="mb-6 p-4 rounded-xl bg-rose-950/40 border border-rose-800/60 text-rose-300 text-xs sm:text-sm flex items-start space-x-3">
              <span className="text-rose-400 text-base">❌</span>
              <div>
                <strong className="font-semibold block mb-0.5">Upload Failed:</strong>
                <span>{uploadError}</span>
              </div>
            </div>
          )}

          {/* Drag & Drop Zone */}
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-2xl p-8 sm:p-12 text-center cursor-pointer transition-all duration-200 ${
              isDragging
                ? "border-indigo-500 bg-indigo-950/30 scale-[1.01]"
                : "border-slate-700/80 hover:border-indigo-500/60 hover:bg-slate-800/40 bg-slate-950/40"
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              onChange={handleFileInputChange}
              className="hidden"
            />

            <div className="flex flex-col items-center justify-center space-y-4 pointer-events-none">
              <div className="h-16 w-16 rounded-2xl bg-indigo-600/10 border border-indigo-500/30 flex items-center justify-center text-3xl shadow-inner text-indigo-400">
                📁
              </div>
              <div>
                <p className="text-base font-semibold text-white">
                  {isDragging ? "Drop your resume here" : "Drag and drop your resume here"}
                </p>
                <p className="text-xs text-slate-400 mt-1">
                  or <span className="text-indigo-400 font-medium underline">browse from your computer</span>
                </p>
              </div>
              <div className="flex items-center space-x-2 text-[11px] text-slate-500">
                <span>PDF or DOCX</span>
                <span>•</span>
                <span>Max 5 MB</span>
              </div>
            </div>
          </div>

          {/* Selected File Details Box */}
          {selectedFile && (
            <div className="mt-6 p-4 rounded-xl bg-slate-950 border border-indigo-900/40 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="flex items-center space-x-3.5 min-w-0">
                <div className="h-10 w-10 shrink-0 rounded-lg bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-xl text-indigo-400 font-bold">
                  {selectedFile.name.endsWith(".pdf") ? "📄" : "📝"}
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-white truncate">
                    {selectedFile.name}
                  </p>
                  <p className="text-xs text-slate-400 font-mono">
                    {formatFileSize(selectedFile.size)} • {selectedFile.type || "Document"}
                  </p>
                </div>
              </div>

              <div className="flex items-center space-x-2 shrink-0">
                <button
                  type="button"
                  onClick={handleClearSelectedFile}
                  disabled={isUploading}
                  className="px-3 py-1.5 text-xs font-medium text-slate-400 hover:text-rose-400 bg-slate-900 hover:bg-rose-950/30 border border-slate-800 hover:border-rose-900/50 rounded-lg transition disabled:opacity-50"
                >
                  Remove
                </button>

                <button
                  type="button"
                  onClick={handleUpload}
                  disabled={isUploading || !!uploadSuccess}
                  className="px-4 py-1.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg shadow-lg shadow-indigo-600/30 transition disabled:opacity-50 flex items-center space-x-1.5"
                >
                  {isUploading ? (
                    <>
                      <div className="animate-spin h-3.5 w-3.5 border-2 border-white border-t-transparent rounded-full" />
                      <span>Uploading...</span>
                    </>
                  ) : uploadSuccess ? (
                    <span>Uploaded ✓</span>
                  ) : (
                    <span>Upload Resume</span>
                  )}
                </button>
              </div>
            </div>
          )}

          {/* Upload Success Alert */}
          {uploadSuccess && (
            <div className="mt-6 p-4 rounded-xl bg-emerald-950/40 border border-emerald-800/60 text-emerald-300 text-xs sm:text-sm">
              <div className="flex items-start space-x-3">
                <span className="text-emerald-400 text-lg">✓</span>
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <strong className="font-semibold block text-emerald-200">Upload Successful!</strong>
                    <div className="flex items-center space-x-2">
                      <span className="px-2 py-0.5 rounded-full bg-emerald-900 text-emerald-300 border border-emerald-700 text-[10px] font-bold uppercase">
                        Version {uploadSuccess.version_number}
                      </span>
                      {uploadSuccess.is_active && (
                        <span className="px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-500/50 text-[10px] font-extrabold uppercase animate-pulse">
                          Active Version
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mt-2 pt-2 border-t border-emerald-900/50 text-xs">
                    <div>
                      <span className="text-emerald-500/80 block uppercase text-[10px] font-bold">Resume ID</span>
                      <span className="font-mono font-semibold text-emerald-200">#{uploadSuccess.id}</span>
                    </div>
                    <div>
                      <span className="text-emerald-500/80 block uppercase text-[10px] font-bold">Stored Filename</span>
                      <span className="truncate block text-emerald-200 font-medium">{uploadSuccess.original_filename}</span>
                    </div>
                    <div>
                      <span className="text-emerald-500/80 block uppercase text-[10px] font-bold">Status</span>
                      <span className="inline-block px-2 py-0.5 rounded bg-emerald-900/60 text-emerald-300 text-[10px] font-bold uppercase">
                        {uploadSuccess.status}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Action: Parse Resume Step */}
        {uploadSuccess && (
          <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-6 sm:p-8 shadow-xl backdrop-blur animate-fadeIn">
            <div className="flex items-center space-x-3 mb-4 pb-3 border-b border-slate-800">
              <div className="h-8 w-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 text-base">
                ⚙️
              </div>
              <div>
                <h2 className="text-base font-bold text-white">Next Step: Text Extraction</h2>
                <p className="text-xs text-slate-400">
                  Parse the stored document with PyMuPDF/python-docx to extract readable plain text.
                </p>
              </div>
            </div>

            {/* Parse Error Alert */}
            {parseError && (
              <div className="mb-6 p-4 rounded-xl bg-rose-950/40 border border-rose-800/60 text-rose-300 text-xs sm:text-sm flex items-start space-x-3">
                <span className="text-rose-400 text-base">❌</span>
                <div>
                  <strong className="font-semibold block mb-0.5">Extraction Failed:</strong>
                  <span>{parseError}</span>
                </div>
              </div>
            )}

            {!parseSuccess ? (
              <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-4 rounded-xl bg-slate-950 border border-slate-800/80">
                <div className="text-xs text-slate-300">
                  Ready to parse <span className="text-indigo-300 font-semibold font-mono">{uploadSuccess.original_filename}</span>.
                </div>
                <button
                  type="button"
                  onClick={handleParse}
                  disabled={isParsing}
                  className="w-full sm:w-auto px-5 py-2 text-xs font-semibold text-white bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 rounded-xl shadow-lg shadow-indigo-500/20 transition flex items-center justify-center space-x-2 disabled:opacity-50"
                >
                  {isParsing ? (
                    <>
                      <div className="animate-spin h-3.5 w-3.5 border-2 border-white border-t-transparent rounded-full" />
                      <span>Parsing Document...</span>
                    </>
                  ) : (
                    <>
                      <span>⚡ Parse Resume</span>
                    </>
                  )}
                </button>
              </div>
            ) : (
              /* Parse Success Panel */
              <div className="space-y-6">
                <div className="p-4 rounded-xl bg-emerald-950/30 border border-emerald-800/50 text-emerald-300 text-xs sm:text-sm">
                  <div className="flex items-start space-x-3">
                    <span className="text-emerald-400 text-lg">✓</span>
                    <div className="flex-1">
                      <strong className="font-semibold block text-emerald-200">Text Extracted Successfully!</strong>
                      <p className="text-xs text-emerald-400/90 mt-0.5">
                        {parseSuccess.message}
                      </p>
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-3 pt-3 border-t border-emerald-900/40 text-xs">
                        <div>
                          <span className="text-slate-400 block uppercase text-[10px] font-bold">Resume ID</span>
                          <span className="font-mono font-semibold text-white">#{parseSuccess.id}</span>
                        </div>
                        <div>
                          <span className="text-slate-400 block uppercase text-[10px] font-bold">Extraction Status</span>
                          <span className="inline-block px-2 py-0.5 rounded bg-emerald-900/60 text-emerald-300 text-[10px] font-bold uppercase">
                            {parseSuccess.status}
                          </span>
                        </div>
                        <div>
                          <span className="text-slate-400 block uppercase text-[10px] font-bold">Extracted Text Length</span>
                          <span className="font-mono font-semibold text-indigo-300">{parseSuccess.extracted_text_length} characters</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-2">
                  <button
                    type="button"
                    onClick={handleClearSelectedFile}
                    className="text-xs px-4 py-2 text-slate-400 hover:text-slate-200 transition"
                  >
                    + Upload Another Resume
                  </button>

                  <div className="flex flex-col sm:flex-row items-center gap-3 w-full sm:w-auto">
                    <Link
                      href="/dashboard"
                      className="w-full sm:w-auto px-4 py-2.5 text-xs font-semibold text-slate-300 bg-slate-900 hover:bg-slate-800 border border-slate-800 rounded-xl transition text-center"
                    >
                      Dashboard
                    </Link>

                    <Link
                      href={`/resume/${parseSuccess.id}/analysis`}
                      className="w-full sm:w-auto px-6 py-2.5 text-xs font-semibold text-white bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 rounded-xl shadow-lg shadow-indigo-500/25 transition text-center flex items-center justify-center space-x-2"
                    >
                      <span>Analyze Resume Structure</span>
                      <span>→</span>
                    </Link>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
