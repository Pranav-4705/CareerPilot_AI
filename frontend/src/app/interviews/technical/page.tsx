"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { ApiError, createVoiceInterviewTokenApi } from "@/lib/api";
import type {
  RemoteParticipant,
  RemoteTrack,
  RemoteTrackPublication,
  Room,
  TranscriptionSegment,
} from "livekit-client";

export type RealtimeState =
  | "Ready to start"
  | "Connecting"
  | "Interviewer speaking"
  | "Listening"
  | "Processing"
  | "Interview ended"
  | "Error";

export type MicStatus = "idle" | "requesting" | "on" | "denied" | "error";

interface TranscriptLine {
  id: string;
  speaker: "ai" | "you";
  text: string;
}

function micLabel(status: MicStatus): string {
  switch (status) {
    case "idle":
      return "Microphone off";
    case "requesting":
      return "Requesting microphone…";
    case "on":
      return "Microphone active";
    case "denied":
      return "Permission denied";
    case "error":
      return "Microphone error";
  }
}

function stateBadgeColor(state: RealtimeState): string {
  switch (state) {
    case "Interviewer speaking":
      return "bg-purple-400 shadow-lg shadow-purple-500/50 animate-pulse";
    case "Listening":
      return "bg-emerald-400 shadow-lg shadow-emerald-400/50 animate-pulse";
    case "Processing":
      return "bg-amber-400 shadow-lg shadow-amber-400/50 animate-pulse";
    case "Connecting":
      return "bg-blue-400 shadow-lg shadow-blue-400/50 animate-pulse";
    case "Interview ended":
      return "bg-slate-400";
    case "Error":
      return "bg-rose-500 shadow-lg shadow-rose-500/50";
    default:
      return "bg-slate-600";
  }
}

function describeMediaError(err: unknown): { message: string; denied: boolean } {
  const name =
    err && typeof err === "object" && "name" in err ? String((err as { name: string }).name) : "";
  if (name === "NotAllowedError" || name === "PermissionDeniedError") {
    return {
      denied: true,
      message:
        "Microphone permission was denied. Please allow microphone access in your browser settings and try again.",
    };
  }
  if (name === "NotFoundError" || name === "DevicesNotFoundError") {
    return { denied: false, message: "No microphone detected. Please connect a microphone and try again." };
  }
  if (err instanceof Error && err.message) {
    return { denied: false, message: err.message };
  }
  return { denied: false, message: "Could not access the microphone." };
}

export default function TechnicalInterviewPage() {
  const router = useRouter();
  const { user, token, loading: authLoading, isAuthenticated, logout } = useAuth();

  const roomRef = useRef<Room | null>(null);
  const audioHostRef = useRef<HTMLDivElement | null>(null);
  const transcriptEndRef = useRef<HTMLDivElement | null>(null);
  const userEndedRef = useRef(false);
  const interviewActiveRef = useRef(false);
  const lastSpeakerRef = useRef<"ai" | "you" | null>(null);

  const [realtimeState, setRealtimeState] = useState<RealtimeState>("Ready to start");
  const [micStatus, setMicStatus] = useState<MicStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [roomName, setRoomName] = useState<string | null>(null);
  const [transcript, setTranscript] = useState<TranscriptLine[]>([]);
  const [starting, setStarting] = useState(false);

  const busy = starting || realtimeState === "Connecting";
  const inSession =
    realtimeState === "Connecting" ||
    realtimeState === "Interviewer speaking" ||
    realtimeState === "Listening" ||
    realtimeState === "Processing";

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [authLoading, isAuthenticated, router]);

  // Auto-scroll transcript to bottom
  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [transcript]);

  const detachRemoteAudio = useCallback((track: RemoteTrack) => {
    track.detach().forEach((el) => el.remove());
  }, []);

  const cleanupRoom = useCallback(async () => {
    const room = roomRef.current;
    roomRef.current = null;
    interviewActiveRef.current = false;
    lastSpeakerRef.current = null;
    if (!room) return;

    try {
      // 1. Unpublish and stop local tracks
      Array.from(room.localParticipant.trackPublications.values()).forEach((pub) => {
        pub.track?.stop();
      });

      // 2. Remove all attached remote audio elements
      if (audioHostRef.current) {
        audioHostRef.current.innerHTML = "";
      }

      // 3. Remove all listeners
      room.removeAllListeners();

      // 4. Disconnect
      await room.disconnect(true);
    } catch {
      // Room may already be closed
    }
  }, []);

  const applyTranscriptions = useCallback(
    (segments: TranscriptionSegment[], participant?: RemoteParticipant | null, isLocal?: boolean) => {
      const speaker: "ai" | "you" = isLocal ? "you" : "ai";
      setTranscript((prev) => {
        const next = [...prev];
        for (const segment of segments) {
          const text = (segment.text || "").trim();
          if (!text) continue;
          const id = `${speaker}-${segment.id || `${participant?.identity || "speaker"}-${segment.firstReceivedTime}`}`;
          const existing = next.findIndex((line) => line.id === id);
          if (existing >= 0) {
            next[existing] = { ...next[existing], text };
          } else {
            next.push({ id, speaker, text });
          }
        }
        return next;
      });
    },
    []
  );

  const endInterview = useCallback(
    async (reason: RealtimeState = "Interview ended") => {
      userEndedRef.current = true;
      await cleanupRoom();
      setMicStatus("idle");
      setRealtimeState(reason);
    },
    [cleanupRoom]
  );

  const startInterview = useCallback(async () => {
    if (!token || busy || inSession) return;

    userEndedRef.current = false;
    lastSpeakerRef.current = null;
    setStarting(true);
    setError(null);
    setTranscript([]);
    setRoomName(null);
    setRealtimeState("Connecting");
    setMicStatus("requesting");

    try {
      // 1. Pre-flight microphone permission check
      let preflightStream: MediaStream | null = null;
      try {
        preflightStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
      } catch (err) {
        const described = describeMediaError(err);
        setMicStatus(described.denied ? "denied" : "error");
        setRealtimeState("Error");
        setError(described.message);
        return;
      } finally {
        preflightStream?.getTracks().forEach((track) => track.stop());
      }

      setMicStatus("on");

      // 2. Fetch LiveKit connection token from existing CareerPilot backend
      let connection;
      try {
        connection = await createVoiceInterviewTokenApi(token);
      } catch (err) {
        setRealtimeState("Error");
        setMicStatus("idle");
        if (err instanceof ApiError) {
          if (err.status === 401) {
            setError("Your session expired. Please sign in again.");
            logout();
            router.push("/login");
            return;
          }
          if (err.status === 503) {
            setError(
              err.message ||
                "LiveKit is not configured on the backend. Please check LIVEKIT_URL, LIVEKIT_API_KEY, and LIVEKIT_API_SECRET."
            );
            return;
          }
          setError(err.message || "Failed to create the interview session.");
        } else {
          setError("Unable to connect to the CareerPilot API. Please ensure the backend server is running.");
        }
        return;
      }

      setRoomName(connection.room_name);

      // 3. Import LiveKit Client SDK dynamically
      const livekit = await import("livekit-client");
      const { Room, RoomEvent, Track, ConnectionState } = livekit;

      const room = new Room({
        adaptiveStream: true,
        dynacast: true,
        audioCaptureDefaults: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      roomRef.current = room;
      interviewActiveRef.current = true;

      // Handle subscribed remote audio track (AI interviewer voice)
      room.on(
        RoomEvent.TrackSubscribed,
        (track: RemoteTrack, _pub: RemoteTrackPublication, participant: RemoteParticipant) => {
          if (track.kind === Track.Kind.Audio) {
            const el = track.attach();
            el.autoplay = true;
            el.dataset.participant = participant.identity;
            audioHostRef.current?.appendChild(el);
            el.play().catch((playErr) => {
              console.warn("Remote audio play blocked:", playErr);
            });
            void room.startAudio();
            setRealtimeState("Interviewer speaking");
            lastSpeakerRef.current = "ai";
          }
        }
      );

      room.on(RoomEvent.TrackUnsubscribed, (track: RemoteTrack) => {
        detachRemoteAudio(track);
      });

      // Participant events
      room.on(RoomEvent.ParticipantConnected, () => {
        if (!interviewActiveRef.current) return;
        setRealtimeState("Connecting");
      });

      room.on(RoomEvent.ParticipantDisconnected, () => {
        if (userEndedRef.current) return;
        if (room.remoteParticipants.size === 0) {
          setRealtimeState("Interview ended");
          setError("The interviewer has completed the session and disconnected.");
          void endInterview("Interview ended");
        }
      });

      room.on(RoomEvent.Disconnected, () => {
        if (userEndedRef.current) return;
        interviewActiveRef.current = false;
        setMicStatus("idle");
        setRealtimeState("Interview ended");
      });

      room.on(RoomEvent.ConnectionStateChanged, (state) => {
        if (state === ConnectionState.Disconnected && !userEndedRef.current && interviewActiveRef.current) {
          setError("Lost connection to the interview room.");
          setRealtimeState("Error");
        }
      });

      // Transcriptions (AI Interviewer and Candidate speech)
      room.on(
        RoomEvent.TranscriptionReceived,
        (segments: TranscriptionSegment[], participant) => {
          const isLocal = !participant || participant.identity === room.localParticipant.identity;
          applyTranscriptions(segments, participant as RemoteParticipant | undefined, isLocal);

          // Update realtime state based on transcription activity
          if (isLocal) {
            const anyFinal = segments.some((s) => s.final);
            if (anyFinal) {
              setRealtimeState("Processing");
              lastSpeakerRef.current = "you";
            } else {
              setRealtimeState("Listening");
            }
          } else {
            setRealtimeState("Interviewer speaking");
            lastSpeakerRef.current = "ai";
          }
        }
      );

      // Chat / text messages fallback
      room.on(RoomEvent.ChatMessage, (message, participant) => {
        const text = (message.message || "").trim();
        if (!text) return;
        const isLocal = !participant || participant.identity === room.localParticipant.identity;
        applyTranscriptions(
          [
            {
              id: message.id,
              text,
              language: "en",
              startTime: message.timestamp,
              endTime: message.timestamp,
              final: true,
              firstReceivedTime: message.timestamp,
              lastReceivedTime: message.editTimestamp || message.timestamp,
            },
          ],
          participant as RemoteParticipant | undefined,
          isLocal
        );
      });

      // Data packets fallback
      room.on(RoomEvent.DataReceived, (payload: Uint8Array, participant) => {
        try {
          const str = new TextDecoder().decode(payload);
          const data = JSON.parse(str);
          if (data && typeof data === "object") {
            const text = (data.text || data.message || "").trim();
            if (text) {
              const isLocal = participant?.identity === room.localParticipant.identity;
              setTranscript((prev) => [
                ...prev,
                {
                  id: `data-${Date.now()}-${Math.random()}`,
                  speaker: isLocal ? "you" : "ai",
                  text,
                },
              ]);
            }
          }
        } catch {
          // Non-JSON payload
        }
      });

      // Active speakers tracking for: Interviewer speaking / Listening / Processing
      room.on(RoomEvent.ActiveSpeakersChanged, (speakers) => {
        if (!interviewActiveRef.current) return;
        const localId = room.localParticipant.identity;
        const agentSpeaker = speakers.find((s) => s.identity !== localId);
        const localSpeaker = speakers.find((s) => s.identity === localId);

        if (agentSpeaker) {
          lastSpeakerRef.current = "ai";
          setRealtimeState("Interviewer speaking");
        } else if (localSpeaker) {
          lastSpeakerRef.current = "you";
          setRealtimeState("Listening");
        } else {
          // No one actively speaking right now
          if (lastSpeakerRef.current === "you") {
            // User finished speaking, backend STT/LLM/TTS is processing
            setRealtimeState("Processing");
          } else if (lastSpeakerRef.current === "ai") {
            // Agent finished speaking, waiting for user response
            setRealtimeState("Listening");
          }
        }
      });

      room.on(RoomEvent.MediaDevicesError, (err: Error) => {
        const described = describeMediaError(err);
        setMicStatus(described.denied ? "denied" : "error");
        setError(described.message);
        setRealtimeState("Error");
      });

      // 4. Connect to LiveKit room
      try {
        await room.connect(connection.url, connection.token);
      } catch (err) {
        await cleanupRoom();
        setRealtimeState("Error");
        setMicStatus("idle");
        setError(
          err instanceof Error
            ? `LiveKit connection error: ${err.message}`
            : "Could not connect to LiveKit room. Please check LIVEKIT_URL."
        );
        return;
      }

      // 5. Publish microphone
      try {
        await room.startAudio();
        await room.localParticipant.setMicrophoneEnabled(true);
        setMicStatus("on");
      } catch (err) {
        const described = describeMediaError(err);
        setMicStatus(described.denied ? "denied" : "error");
        setError(described.message);
        await cleanupRoom();
        setRealtimeState("Error");
        return;
      }

      // If agent is not yet speaking, indicate waiting / connecting
      if (room.remoteParticipants.size === 0) {
        setRealtimeState("Connecting");
      } else {
        setRealtimeState("Listening");
      }
    } finally {
      setStarting(false);
    }
  }, [
    applyTranscriptions,
    busy,
    cleanupRoom,
    detachRemoteAudio,
    endInterview,
    inSession,
    logout,
    router,
    token,
  ]);

  // Teardown on unmount
  useEffect(() => {
    return () => {
      userEndedRef.current = true;
      void cleanupRoom();
    };
  }, [cleanupRoom]);

  const handleLogout = () => {
    void endInterview("Interview ended");
    logout();
    router.push("/login");
  };

  if (authLoading || !user) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-slate-950 text-slate-100">
        <div className="animate-spin h-10 w-10 border-3 border-indigo-500 border-t-transparent rounded-full" />
        <p className="mt-4 text-sm text-slate-400 font-medium">Loading interview console…</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 text-slate-100">
      {/* Header */}
      <header className="border-b border-slate-800/80 backdrop-blur sticky top-0 z-50 bg-slate-950/80">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <Link href="/dashboard" className="flex items-center space-x-3 group">
            <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center text-white font-bold shadow-lg shadow-indigo-500/20">
              CP
            </div>
            <div>
              <span className="text-lg font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-indigo-300 to-purple-400">
                CareerPilot AI
              </span>
              <span className="ml-2 text-xs uppercase tracking-widest font-semibold px-2 py-0.5 rounded-full bg-purple-950 text-purple-300 border border-purple-800/50">
                Technical Interview
              </span>
            </div>
          </Link>
          <div className="flex items-center space-x-3">
            <Link
              href="/dashboard"
              className="text-xs px-3 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 font-medium transition"
            >
              Dashboard
            </Link>
            <button
              type="button"
              onClick={handleLogout}
              className="text-xs px-3 py-1.5 rounded-xl bg-slate-800/80 hover:bg-rose-900/40 hover:text-rose-300 border border-slate-700/80 text-slate-300 font-medium transition"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-4xl mx-auto px-4 sm:px-6 py-8 w-full space-y-6">
        {/* Session Card */}
        <section className="p-6 rounded-2xl bg-slate-900/80 border border-purple-900/40 space-y-5 shadow-xl">
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight">Voice Technical Interview</h1>
            <p className="mt-1 text-xs text-slate-400 leading-relaxed">
              Real-time voice interview powered by LiveKit. The AI interviewer greets you, asks 3 technical
              questions one by one with follow-ups, and closes the session.
            </p>
          </div>

          {/* Realtime Status Indicator */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {/* Realtime State Display */}
            <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 flex items-center space-x-3.5">
              <span className={`h-3.5 w-3.5 rounded-full shrink-0 ${stateBadgeColor(realtimeState)}`} />
              <div>
                <p className="text-[10px] uppercase tracking-wider text-slate-500 font-bold">
                  Realtime Interview State
                </p>
                <p className="text-sm font-bold text-white mt-0.5">{realtimeState}</p>
              </div>
            </div>

            {/* Microphone Status Display */}
            <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 flex items-center space-x-3.5">
              <span
                className={`h-3.5 w-3.5 rounded-full shrink-0 ${
                  micStatus === "on"
                    ? "bg-emerald-400 shadow-md shadow-emerald-400/50"
                    : micStatus === "denied" || micStatus === "error"
                    ? "bg-rose-500"
                    : "bg-slate-600"
                }`}
              />
              <div>
                <p className="text-[10px] uppercase tracking-wider text-slate-500 font-bold">Microphone</p>
                <p className="text-sm font-semibold text-slate-200 mt-0.5">{micLabel(micStatus)}</p>
              </div>
            </div>
          </div>

          {roomName && (
            <p className="text-[11px] text-slate-500 font-mono">
              LiveKit Room: <span className="text-slate-400">{roomName}</span>
            </p>
          )}

          {error && (
            <div className="p-3.5 rounded-xl bg-rose-950/40 border border-rose-800/60 text-rose-300 text-xs leading-relaxed">
              <span className="font-semibold">Notice:</span> {error}
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex items-center gap-3 pt-1">
            <button
              type="button"
              onClick={() => void startInterview()}
              disabled={busy || inSession}
              className="px-5 py-2.5 text-xs font-semibold text-white bg-purple-600 hover:bg-purple-500 rounded-xl transition shadow-lg shadow-purple-600/25 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {busy ? "Starting…" : "Start Interview"}
            </button>
            <button
              type="button"
              onClick={() => void endInterview("Interview ended")}
              disabled={!inSession}
              className="px-5 py-2.5 text-xs font-semibold text-rose-200 bg-rose-950/50 hover:bg-rose-900/60 border border-rose-800/70 rounded-xl transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              End Interview
            </button>
          </div>
        </section>

        {/* Live Conversation / Transcript Area */}
        <section className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 min-h-[340px] flex flex-col shadow-lg">
          <div className="flex items-center justify-between mb-3 border-b border-slate-800/60 pb-2">
            <h2 className="text-sm font-bold text-white tracking-wide">Live Conversation & Transcript</h2>
            <span className="text-[11px] text-slate-400 font-mono">
              {transcript.length} {transcript.length === 1 ? "entry" : "entries"}
            </span>
          </div>

          <div className="flex-1 space-y-3 overflow-y-auto max-h-[460px] pr-1">
            {transcript.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-48 text-center px-4">
                <p className="text-xs text-slate-400 font-medium">
                  Transcript will appear here once the interview starts.
                </p>
                <p className="text-[11px] text-slate-500 mt-1">
                  Speak clearly into your microphone after the AI interviewer asks each question.
                </p>
              </div>
            ) : (
              transcript.map((line) => (
                <div
                  key={line.id}
                  className={`p-3.5 rounded-xl text-xs leading-relaxed transition-all ${
                    line.speaker === "ai"
                      ? "bg-purple-950/40 border border-purple-900/50 text-purple-100 shadow-sm"
                      : "bg-slate-950/80 border border-slate-800 text-slate-200 shadow-sm"
                  }`}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <p
                      className={`text-[10px] uppercase tracking-wider font-bold ${
                        line.speaker === "ai" ? "text-purple-300" : "text-indigo-300"
                      }`}
                    >
                      {line.speaker === "ai" ? "🤖 AI Interviewer" : "👤 Candidate (You)"}
                    </p>
                  </div>
                  <p className="whitespace-pre-wrap">{line.text}</p>
                </div>
              ))
            )}
            <div ref={transcriptEndRef} />
          </div>
        </section>
      </main>

      {/* Hidden audio element container for remote LiveKit interviewer audio tracks */}
      <div ref={audioHostRef} className="hidden" aria-hidden="true" />
    </div>
  );
}
