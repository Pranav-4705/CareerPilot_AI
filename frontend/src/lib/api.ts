const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface UserProfile {
  id: number;
  name: string;
  email: string;
  created_at: string;
  updated_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface RegisterPayload {
  name: string;
  email: string;
  password: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface ResumeUploadResponse {
  id: number;
  original_filename: string;
  version_number: number;
  is_active: boolean;
  uploaded_at: string;
  status: string;
  message: string;
}

export interface ResumeParseResponse {
  id: number;
  original_filename: string;
  version_number?: number;
  is_active?: boolean;
  status: string;
  extracted_text_length: number;
  message: string;
}

export interface ResumeDetailResponse {
  id: number;
  user_id: number;
  original_filename: string;
  file_path: string;
  version_number: number;
  is_active: boolean;
  extracted_text?: string | null;
  uploaded_at: string;
}

export interface ResumeHistoryItem {
  id: number;
  original_filename: string;
  version_number: number;
  is_active: boolean;
  uploaded_at: string;
  status: string;
  is_parsed: boolean;
  has_analysis: boolean;
  has_ats_score: boolean;
  ats_score: number | null;
}

export interface SectionItem {
  title: string;
  details: string[];
  raw_text: string;
}

export interface ResumeAnalysisResponse {
  id: number;
  resume_id: number;
  extracted_skills: string[];
  education: SectionItem[];
  experience: SectionItem[];
  projects: SectionItem[];
  certifications: SectionItem[];
  created_at: string;
  message: string;
}

export interface ComponentScores {
  section_structure: number;
  skills_coverage: number;
  keyword_quality: number;
  experience_depth: number;
  readability_format: number;
}

export interface ATSAnalysisResponse {
  id: number;
  resume_id: number;
  ats_score: number;
  component_scores: ComponentScores;
  strengths: string[];
  weaknesses: string[];
  missing_skills: string[];
  recommendations: string[];
  created_at: string;
  message: string;
}

export class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(message: string, status: number, data?: unknown) {
    super(message);
    this.status = status;
    this.data = data;
    this.name = "ApiError";
  }
}

/**
 * Raises an ApiError carrying the backend's `detail` message.
 *
 * Separate from `handleResponse` because the synthesis endpoint answers with
 * binary audio on success, so its body must not be parsed as JSON.
 */
async function raiseApiError(res: Response): Promise<never> {
  let errorMessage = `Request failed with status ${res.status}`;
  let data: unknown = null;
  try {
    data = await res.json();
    if (data && typeof data === "object" && "detail" in data) {
      const detail = (data as { detail: unknown }).detail;
      if (typeof detail === "string") {
        errorMessage = detail;
      } else if (Array.isArray(detail)) {
        errorMessage = detail.map((e: { msg?: string }) => e.msg || JSON.stringify(e)).join(", ");
      }
    }
  } catch {
    // Non-JSON response
  }
  throw new ApiError(errorMessage, res.status, data);
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    return raiseApiError(res);
  }
  return res.json() as Promise<T>;
}

export async function fetchHealth() {
  const res = await fetch(`${API_BASE_URL}/api/health`, {
    cache: "no-store",
  });
  return handleResponse<{ status: string; message: string; service: string; version: string }>(res);
}

export async function registerApi(payload: RegisterPayload): Promise<UserProfile> {
  const res = await fetch(`${API_BASE_URL}/api/v1/auth/register`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  return handleResponse<UserProfile>(res);
}

export async function loginApi(payload: LoginPayload): Promise<TokenResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  return handleResponse<TokenResponse>(res);
}

export async function getMeApi(token: string): Promise<UserProfile> {
  const res = await fetch(`${API_BASE_URL}/api/v1/auth/me`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return handleResponse<UserProfile>(res);
}

export interface VoiceInterviewTokenResponse {
  url: string;
  token: string;
  room_name: string;
  identity: string;
  agent_name: string;
}

export async function createVoiceInterviewTokenApi(
  token: string
): Promise<VoiceInterviewTokenResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/interviews/voice/token`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return handleResponse<VoiceInterviewTokenResponse>(res);
}

export async function uploadResumeApi(file: File, token: string): Promise<ResumeUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE_URL}/api/v1/resumes/upload`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      // Fetch automatically sets multipart/form-data with boundary
    },
    body: formData,
  });
  return handleResponse<ResumeUploadResponse>(res);
}

export async function parseResumeApi(resumeId: number, token: string): Promise<ResumeParseResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/resumes/${resumeId}/parse`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return handleResponse<ResumeParseResponse>(res);
}

export async function analyzeResumeApi(resumeId: number, token: string): Promise<ResumeAnalysisResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/resumes/${resumeId}/analyze`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return handleResponse<ResumeAnalysisResponse>(res);
}

export async function atsAnalyzeResumeApi(resumeId: number, token: string): Promise<ATSAnalysisResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/resumes/${resumeId}/ats-analyze`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return handleResponse<ATSAnalysisResponse>(res);
}

export async function getResumeApi(resumeId: number, token: string): Promise<ResumeDetailResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/resumes/${resumeId}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return handleResponse<ResumeDetailResponse>(res);
}

export async function getResumesApi(token: string): Promise<ResumeHistoryItem[]> {
  const res = await fetch(`${API_BASE_URL}/api/v1/resumes`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return handleResponse<ResumeHistoryItem[]>(res);
}

export async function getActiveResumeApi(token: string): Promise<ResumeDetailResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/resumes/active`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return handleResponse<ResumeDetailResponse>(res);
}

export async function activateResumeApi(resumeId: number, token: string): Promise<ResumeDetailResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/resumes/${resumeId}/activate`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return handleResponse<ResumeDetailResponse>(res);
}

export interface DeleteResumeResponse {
  message: string;
  id: number;
  promoted_active_id?: number | null;
}

export async function deleteResumeApi(resumeId: number, token: string): Promise<DeleteResumeResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/resumes/${resumeId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return handleResponse<DeleteResumeResponse>(res);
}

// -------------------------------------------------------------
// Phase 6: Job Descriptions & Semantic Resume Matching
// -------------------------------------------------------------

export interface JobDescriptionCreate {
  title: string;
  company?: string;
  description: string;
}

export interface JobDescriptionResponse {
  id: number;
  user_id?: number;
  title: string;
  company?: string | null;
  description: string;
  extracted_skills?: string[];
  extracted_keywords?: string[];
  required_experience?: { signals?: string[]; count?: number } | Record<string, unknown>;
  education_requirements?: string[];
  responsibilities?: string[];
  created_at: string;
  updated_at?: string | null;
}

export interface JobAnalyzeResponse {
  id: number;
  job_id: number;
  required_skills: string[];
  experience_requirements: string[];
  education_requirements: string[];
  responsibilities: string[];
  extracted_keywords: string[];
  message: string;
}

export interface ComponentMatchScores {
  skills_match: number;
  experience_match: number;
  education_match: number;
  responsibility_match: number;
}

export interface JobMatchResponse {
  id: number;
  user_id?: number;
  resume_id: number;
  job_description_id: number;
  match_score: number;
  component_scores?: ComponentMatchScores;
  matched_skills?: string[];
  missing_skills?: string[];
  matched_keywords?: string[];
  missing_keywords?: string[];
  keyword_gaps?: string[];
  requirement_gaps?: string[];
  experience_match?: boolean;
  education_match?: boolean;
  recommendations?: string[];
  skill_match_score?: number;
  semantic_similarity_score?: number;
  created_at: string;
  message?: string;
}

export async function createJobApi(
  data: JobDescriptionCreate,
  token: string
): Promise<JobDescriptionResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/jobs`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(data),
  });
  return handleResponse<JobDescriptionResponse>(res);
}

export async function getJobsApi(token: string): Promise<JobDescriptionResponse[]> {
  const res = await fetch(`${API_BASE_URL}/api/v1/jobs`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return handleResponse<JobDescriptionResponse[]>(res);
}

export async function getJobApi(jobId: number, token: string): Promise<JobDescriptionResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/jobs/${jobId}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return handleResponse<JobDescriptionResponse>(res);
}

export async function analyzeJobApi(jobId: number, token: string): Promise<JobAnalyzeResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/jobs/${jobId}/analyze`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return handleResponse<JobAnalyzeResponse>(res);
}

export async function matchJobResumeApi(
  jobId: number,
  resumeId: number,
  token: string
): Promise<JobMatchResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/jobs/${jobId}/match/${resumeId}`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return handleResponse<JobMatchResponse>(res);
}

export const matchResumeToJobApi = matchJobResumeApi;

export interface PrioritizedSkill {
  name: string;
  priority: "high" | "medium" | "low" | "needs_review";
}

export interface SkillGapInsight {
  match_percentage: number;
  matched_skills: string[];
  missing_skills: string[];
  prioritized_missing_skills: PrioritizedSkill[];
  explanation?: string | null;
}

export interface ExperienceInsight {
  status: "meets" | "does_not_meet" | "unknown" | "not_specified";
  requirement?: string | null;
  message: string;
}

export interface EducationInsight {
  status: "meets" | "does_not_meet" | "unknown" | "not_specified";
  requirement?: string | null;
  message: string;
}

export interface ResponsibilityInsight {
  alignment_score: number;
  aligned_areas: string[];
  improvement_areas: string[];
}

export interface MatchRecommendation {
  severity: "critical" | "high" | "medium" | "low" | "info";
  message: string;
}

export interface MatchInsightsResponse {
  job_id: number;
  resume_id: number;
  match_score: number;
  strengths: string[];
  skill_gap: SkillGapInsight;
  experience: ExperienceInsight;
  education: EducationInsight;
  responsibilities: ResponsibilityInsight;
  recommendations: MatchRecommendation[];
}

export async function getMatchInsightsApi(
  jobId: number,
  resumeId: number,
  token: string
): Promise<MatchInsightsResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/jobs/${jobId}/match/${resumeId}/insights`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return handleResponse<MatchInsightsResponse>(res);
}

// ==============================================================================
// Phase 8: Technical Interview
// ==============================================================================

export interface InterviewQuestion {
  id: number;
  question_number: number;
  question_text: string;
  topic: string | null;
  difficulty: string | null;
  source_context: string | null;
  created_at: string;
}

export interface InterviewAnswerDetail {
  id: number;
  question_id: number;
  answer_text: string;
  technical_score: number | null;
  relevance_score: number | null;
  depth_score: number | null;
  clarity_score: number | null;
  overall_score: number | null;
  feedback: string | null;
  strengths: string[];
  improvements: string[];
  created_at: string;
}

export interface InterviewQuestionDetail extends InterviewQuestion {
  answer: InterviewAnswerDetail | null;
}

export interface AnswerEvaluation {
  score: number;
  technical_accuracy: number;
  relevance: number;
  depth: number;
  clarity: number;
  feedback: string;
  strengths: string[];
  improvements: string[];
  follow_up_needed: boolean;
}

export interface InterviewSummary {
  overall_score: number;
  technical_knowledge: number;
  problem_solving: number;
  practical_understanding: number;
  strengths: string[];
  improvements: string[];
  summary_text: string;
  /** Saved final evaluation, generated once from the whole conversation. */
  category_scores?: Record<string, number>;
  weaknesses?: string[];
  improvement_suggestions?: string[];
}

export interface StartInterviewResponse {
  interview_id: number;
  status: string;
  total_questions: number;
  current_question_number: number;
  first_question: InterviewQuestion | null;
  resume_id: number;
  resume_filename: string | null;
  resume_version: number | null;
  job_id: number | null;
  job_title: string | null;
}

export interface AnswerTurnResponse {
  interview_id: number;
  question_number: number;
  answer_evaluation: AnswerEvaluation;
  next_question: InterviewQuestion | null;
  completed: boolean;
  overall_score: number | null;
  summary: InterviewSummary | null;
}

export interface TechnicalInterviewDetail {
  id: number;
  user_id: number;
  resume_id: number;
  job_id: number | null;
  status: string;
  current_question_number: number;
  total_questions: number;
  overall_score: number | null;
  summary: InterviewSummary | null;
  started_at: string;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
  current_question: InterviewQuestion | null;
  questions: InterviewQuestionDetail[];
  resume_filename: string | null;
  resume_version: number | null;
  job_title: string | null;
  job_company: string | null;
}

export interface TechnicalInterviewListItem {
  id: number;
  status: string;
  current_question_number: number;
  total_questions: number;
  overall_score: number | null;
  started_at: string;
  completed_at: string | null;
  resume_id: number;
  resume_filename: string | null;
  resume_version: number | null;
  job_id: number | null;
  job_title: string | null;
  job_company: string | null;
}

export async function startInterviewApi(
  payload: { resume_id?: number; job_id?: number; total_questions?: number },
  token: string
): Promise<StartInterviewResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/interviews/technical/start`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
  return handleResponse<StartInterviewResponse>(res);
}

export async function submitInterviewAnswerApi(
  interviewId: number,
  answer: string,
  token: string
): Promise<AnswerTurnResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/interviews/technical/${interviewId}/answer`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ answer }),
  });
  return handleResponse<AnswerTurnResponse>(res);
}

export async function getInterviewApi(
  interviewId: number,
  token: string
): Promise<TechnicalInterviewDetail> {
  const res = await fetch(`${API_BASE_URL}/api/v1/interviews/technical/${interviewId}`, {
    method: "GET",
    headers: { Authorization: `Bearer ${token}` },
  });
  return handleResponse<TechnicalInterviewDetail>(res);
}

export async function listInterviewsApi(token: string): Promise<TechnicalInterviewListItem[]> {
  const res = await fetch(`${API_BASE_URL}/api/v1/interviews/technical`, {
    method: "GET",
    headers: { Authorization: `Bearer ${token}` },
  });
  return handleResponse<TechnicalInterviewListItem[]>(res);
}

export async function completeInterviewApi(
  interviewId: number,
  token: string
): Promise<{ message: string; interview_id: number; status: string; overall_score: number | null }> {
  const res = await fetch(`${API_BASE_URL}/api/v1/interviews/technical/${interviewId}/complete`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
  return handleResponse(res);
}

// ==============================================================================
// Phase 9: HR / Behavioral Interview
// ==============================================================================

export interface HRSTARFeedback {
  situation: string;
  task: string;
  action: string;
  result: string;
  guidance: string;
}

export interface HRAnswerEvaluation {
  relevance_score: number;
  clarity_score: number;
  specificity_score: number;
  communication_score: number;
  self_awareness_score: number;
  behavioral_evidence_score: number;
  overall_score: number;
  feedback: string;
  strengths: string[];
  improvement_points: string[];
  star_feedback: HRSTARFeedback | null;
  follow_up_needed: boolean;
}

export interface HRInterviewQuestion {
  id: number;
  question_number: number;
  question_text: string;
  category: string | null;
  difficulty: string | null;
  source_context: string | null;
  created_at: string;
}

export interface HRInterviewAnswerDetail {
  id: number;
  question_id: number;
  answer_text: string;
  relevance_score: number | null;
  clarity_score: number | null;
  specificity_score: number | null;
  communication_score: number | null;
  self_awareness_score: number | null;
  behavioral_evidence_score: number | null;
  overall_score: number | null;
  feedback: string | null;
  strengths: string[];
  improvement_points: string[];
  star_feedback: HRSTARFeedback | null;
  created_at: string;
}

export interface HRInterviewQuestionDetail extends HRInterviewQuestion {
  answer: HRInterviewAnswerDetail | null;
}

export interface HRInterviewSummary {
  overall_score: number;
  communication: number;
  behavioral_responses: number;
  specificity: number;
  self_awareness: number;
  strengths: string[];
  improvement_areas: string[];
  suggested_practice: string[];
  summary_text: string;
  /** Saved final evaluation, generated once from the whole conversation. */
  category_scores?: Record<string, number>;
  weaknesses?: string[];
  improvement_suggestions?: string[];
}

export interface StartHRInterviewResponse {
  interview_id: number;
  status: string;
  total_questions: number;
  current_question_number: number;
  first_question: HRInterviewQuestion | null;
  resume_id: number;
  resume_filename: string | null;
  resume_version: number | null;
  job_id: number | null;
  job_title: string | null;
}

export interface HRAnswerTurnResponse {
  interview_id: number;
  question_number: number;
  answer_evaluation: HRAnswerEvaluation;
  next_question: HRInterviewQuestion | null;
  completed: boolean;
  overall_score: number | null;
  summary: HRInterviewSummary | null;
}

export interface HRInterviewDetail {
  id: number;
  user_id: number;
  resume_id: number;
  job_id: number | null;
  status: string;
  current_question_number: number;
  total_questions: number;
  overall_score: number | null;
  summary: HRInterviewSummary | null;
  started_at: string;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
  current_question: HRInterviewQuestion | null;
  questions: HRInterviewQuestionDetail[];
  resume_filename: string | null;
  resume_version: number | null;
  job_title: string | null;
  job_company: string | null;
}

export interface HRInterviewListItem {
  id: number;
  status: string;
  current_question_number: number;
  total_questions: number;
  overall_score: number | null;
  started_at: string;
  completed_at: string | null;
  resume_id: number;
  resume_filename: string | null;
  resume_version: number | null;
  job_id: number | null;
  job_title: string | null;
  job_company: string | null;
}

export async function startHRInterviewApi(
  payload: { resume_id?: number; job_id?: number; total_questions?: number },
  token: string
): Promise<StartHRInterviewResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/interviews/hr/start`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
  return handleResponse<StartHRInterviewResponse>(res);
}

export async function submitHRInterviewAnswerApi(
  interviewId: number,
  answer: string,
  token: string
): Promise<HRAnswerTurnResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/interviews/hr/${interviewId}/answer`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ answer }),
  });
  return handleResponse<HRAnswerTurnResponse>(res);
}

export async function getHRInterviewApi(
  interviewId: number,
  token: string
): Promise<HRInterviewDetail> {
  const res = await fetch(`${API_BASE_URL}/api/v1/interviews/hr/${interviewId}`, {
    method: "GET",
    headers: { Authorization: `Bearer ${token}` },
  });
  return handleResponse<HRInterviewDetail>(res);
}

export async function listHRInterviewsApi(token: string): Promise<HRInterviewListItem[]> {
  const res = await fetch(`${API_BASE_URL}/api/v1/interviews/hr`, {
    method: "GET",
    headers: { Authorization: `Bearer ${token}` },
  });
  return handleResponse<HRInterviewListItem[]>(res);
}

export async function completeHRInterviewApi(
  interviewId: number,
  token: string
): Promise<{ message: string; interview_id: number; status: string; overall_score: number | null }> {
  const res = await fetch(`${API_BASE_URL}/api/v1/interviews/hr/${interviewId}/complete`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
  return handleResponse(res);
}

// ==============================================================================
// Local speech: voice-first interviews (Phases C + D)
// ==============================================================================

export interface TranscriptionSegment {
  start: number;
  end: number;
  text: string;
}

export interface TranscriptionResponse {
  transcript: string;
  duration_seconds: number | null;
  language: string | null;
  provider: string;
  model: string | null;
  segment_count: number;
  segments?: TranscriptionSegment[] | null;
}

/**
 * Uploads one audio file for local transcription.
 *
 * The interview flow no longer needs this: live voice audio is streamed as PCM
 * over the live interview WebSocket. It remains for one-shot transcription of
 * a recorded file, and the file name and content type must still match a
 * container the backend accepts.
 */
export async function transcribeAudioApi(file: File, token: string): Promise<TranscriptionResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE_URL}/api/v1/speech/transcribe`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      // Fetch sets multipart/form-data with the boundary itself.
    },
    body: formData,
  });
  return handleResponse<TranscriptionResponse>(res);
}

/**
 * Renders text with the local TTS provider and returns the playable audio.
 *
 * Answers with raw `audio/wav` bytes rather than JSON, so the body is read as a
 * Blob; only errors go through the shared JSON error path.
 */
export async function synthesizeSpeechApi(text: string, token: string): Promise<Blob> {
  const res = await fetch(`${API_BASE_URL}/api/v1/speech/synthesize`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ text }),
  });

  if (!res.ok) {
    return raiseApiError(res);
  }
  return res.blob();
}

export interface SpeechVoicesResponse {
  provider: string;
  default_voice: string;
  voices: string[];
  available: boolean;
  max_text_length: number;
  media_type: string;
}

/** Reports which local voices the backend can render (used for diagnostics). */
export async function getSpeechVoicesApi(token: string): Promise<SpeechVoicesResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/speech/voices`, {
    method: "GET",
    headers: { Authorization: `Bearer ${token}` },
  });
  return handleResponse<SpeechVoicesResponse>(res);
}

