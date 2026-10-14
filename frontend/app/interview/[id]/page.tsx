"use client";
export const dynamic = "force-dynamic";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import toast from "react-hot-toast";
import { Captions, CheckCircle2, Circle, Loader2, Mic, MicOff, PhoneOff, Shield, Video, VideoOff } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import {
  InterviewDetail,
  iceServers,
  interviewService,
  signallingUrl,
} from "@/services/interviewService";

const CLIP_MS = 12000; // standalone audio clips sent for transcription
const POLL_MS = 5000;
const CRITERIA = ["Problem solving", "Technical depth", "Communication"];

type Link = "waiting" | "connecting" | "connected" | "replaced";

export default function InterviewRoomPage() {
  const params = useParams();
  const router = useRouter();
  const id = String(params?.id || "");
  const { isAuthenticated, isLoading } = useAuth();

  const [detail, setDetail] = useState<InterviewDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [link, setLink] = useState<Link>("waiting");
  const [micOn, setMicOn] = useState(true);
  const [camOn, setCamOn] = useState(true);
  const [mediaError, setMediaError] = useState<string | null>(null);
  const [transcribing, setTranscribing] = useState(false);
  const [topicsText, setTopicsText] = useState("");
  const [scores, setScores] = useState<Record<string, number>>(Object.fromEntries(CRITERIA.map((c) => [c, 3])));
  const [notes, setNotes] = useState("");

  const localVideo = useRef<HTMLVideoElement>(null);
  const remoteVideo = useRef<HTMLVideoElement>(null);
  const localStream = useRef<MediaStream | null>(null);
  const pc = useRef<RTCPeerConnection | null>(null);
  const ws = useRef<WebSocket | null>(null);
  const micOnRef = useRef(true);

  const role = detail?.role;
  const canJoin = !!detail && detail.status !== "COMPLETED" && (role === "interviewer" || detail.recording_consent);

  // ---- Load + poll ---------------------------------------------------------
  const load = useCallback(async () => {
    try {
      const d = await interviewService.get(id);
      setDetail(d);
      if (d.topics && !topicsText) setTopicsText(d.topics.join(", "));
    } catch (e: any) {
      setError(e?.message || "Interview not found.");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  useEffect(() => {
    if (isLoading) return;
    if (!isAuthenticated) {
      router.replace("/auth/login");
      return;
    }
    void load();
    const t = setInterval(load, POLL_MS);
    return () => clearInterval(t);
  }, [isLoading, isAuthenticated, load, router]);

  // ---- WebRTC ------------------------------------------------------------
  const send = (message: object) => {
    if (ws.current?.readyState === WebSocket.OPEN) ws.current.send(JSON.stringify(message));
  };

  const newPeer = useCallback(() => {
    pc.current?.close();
    const peer = new RTCPeerConnection({ iceServers: iceServers() });
    localStream.current?.getTracks().forEach((t) => peer.addTrack(t, localStream.current!));
    peer.ontrack = (e) => {
      if (remoteVideo.current) remoteVideo.current.srcObject = e.streams[0];
    };
    peer.onicecandidate = (e) => e.candidate && send({ type: "ice", candidate: e.candidate });
    peer.onconnectionstatechange = () => {
      if (peer.connectionState === "connected") setLink("connected");
      else if (["failed", "disconnected", "closed"].includes(peer.connectionState)) setLink("waiting");
    };
    pc.current = peer;
    return peer;
  }, []);

  const makeOffer = useCallback(async () => {
    setLink("connecting");
    const peer = newPeer();
    const offer = await peer.createOffer();
    await peer.setLocalDescription(offer);
    send({ type: "offer", sdp: peer.localDescription });
  }, [newPeer]);

  useEffect(() => {
    if (!canJoin || !role) return;
    let cancelled = false;

    (async () => {
      try {
        localStream.current = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
        if (localVideo.current) localVideo.current.srcObject = localStream.current;
      } catch {
        setMediaError("Camera/microphone access was denied. Allow it in the browser and reload.");
        return;
      }
      if (cancelled) return;

      const socket = new WebSocket(signallingUrl(id));
      ws.current = socket;
      socket.onmessage = async (event) => {
        const msg = JSON.parse(event.data);
        try {
          if (msg.type === "joined" && role === "interviewer" && msg.peer_present) await makeOffer();
          else if (msg.type === "peer-joined" && role === "interviewer") await makeOffer();
          else if (msg.type === "offer" && role === "candidate") {
            setLink("connecting");
            const peer = newPeer();
            await peer.setRemoteDescription(msg.sdp);
            const answer = await peer.createAnswer();
            await peer.setLocalDescription(answer);
            send({ type: "answer", sdp: peer.localDescription });
          } else if (msg.type === "answer") await pc.current?.setRemoteDescription(msg.sdp);
          else if (msg.type === "ice" && msg.candidate) await pc.current?.addIceCandidate(msg.candidate);
          else if (msg.type === "peer-left" || msg.type === "hangup") {
            pc.current?.close();
            pc.current = null;
            if (remoteVideo.current) remoteVideo.current.srcObject = null;
            setLink("waiting");
          } else if (msg.type === "replaced") setLink("replaced");
        } catch (e) {
          console.error("signalling error", e);
        }
      };
      socket.onclose = (e) => {
        if (e.code === 1008) setError(e.reason || "Not allowed to join this interview.");
      };
    })();

    return () => {
      cancelled = true;
      ws.current?.close();
      pc.current?.close();
      localStream.current?.getTracks().forEach((t) => t.stop());
    };
  }, [canJoin, role, id, makeOffer, newPeer]);

  // ---- Candidate transcription: standalone clips every CLIP_MS ------------
  const transcribeActive =
    role === "candidate" && !!detail?.recording_consent && detail.transcription_available &&
    (detail.status === "READY" || detail.status === "LIVE") && !mediaError;

  useEffect(() => {
    if (!transcribeActive) return;
    let stopped = false;
    let recorder: MediaRecorder | null = null;
    let timer: ReturnType<typeof setTimeout>;

    const recordClip = () => {
      const audio = localStream.current?.getAudioTracks();
      if (stopped || !audio?.length) {
        timer = setTimeout(recordClip, 1000);
        return;
      }
      // A new recorder per clip so each upload is a complete, decodable file.
      recorder = new MediaRecorder(new MediaStream(audio), { mimeType: "audio/webm;codecs=opus" });
      const chunks: Blob[] = [];
      recorder.ondataavailable = (e) => e.data.size && chunks.push(e.data);
      recorder.onstop = () => {
        const clip = new Blob(chunks, { type: "audio/webm" });
        if (micOnRef.current && clip.size > 2000) {
          setTranscribing(true);
          interviewService
            .uploadAudio(id, clip)
            .then((r) => r.segments.length && setDetail((d) => (d ? { ...d, segments: [...d.segments, ...r.segments] } : d)))
            .catch(() => undefined)
            .finally(() => setTranscribing(false));
        }
        if (!stopped) recordClip();
      };
      recorder.start();
      timer = setTimeout(() => recorder?.state === "recording" && recorder.stop(), CLIP_MS);
    };
    recordClip();
    return () => {
      stopped = true;
      clearTimeout(timer);
      if (recorder?.state === "recording") recorder.stop();
    };
  }, [transcribeActive, id]);

  // ---- Controls ----------------------------------------------------------
  const toggleMic = () => {
    const next = !micOn;
    localStream.current?.getAudioTracks().forEach((t) => (t.enabled = next));
    micOnRef.current = next;
    setMicOn(next);
  };
  const toggleCam = () => {
    const next = !camOn;
    localStream.current?.getVideoTracks().forEach((t) => (t.enabled = next));
    setCamOn(next);
  };
  const leave = () => {
    send({ type: "hangup" });
    router.push(role === "interviewer" ? "/admin/interviews" : "/candidate/dashboard");
  };

  const giveConsent = async () => {
    try {
      await interviewService.consent(id);
      await load();
    } catch (e: any) {
      toast.error(e?.message || "Could not record consent.");
    }
  };
  const setStatus = async (status: InterviewDetail["status"]) => {
    try {
      await interviewService.setStatus(id, status);
      if (status === "COMPLETED") send({ type: "hangup" });
      await load();
    } catch (e: any) {
      toast.error(e?.message || "Could not update status.");
    }
  };
  const saveTopics = async () => {
    const topics = topicsText.split(",").map((t) => t.trim()).filter(Boolean);
    try {
      const r = await interviewService.setTopics(id, topics);
      setDetail((d) => (d ? { ...d, topics: r.topics, coverage: r.coverage } : d));
      toast.success("Topics saved.");
    } catch (e: any) {
      toast.error(e?.message || "Could not save topics.");
    }
  };
  const submitScore = async () => {
    try {
      await interviewService.score(id, scores, notes);
      setNotes("");
      toast.success("Score saved.");
      await load();
    } catch (e: any) {
      toast.error(e?.message || "Could not save the score.");
    }
  };

  // ---- Render ------------------------------------------------------------
  if (error) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-3 bg-slate-950 p-6 text-center">
        <p className="text-rose-300">{error}</p>
        <button onClick={() => router.push("/dashboard")} className="text-sm font-semibold text-indigo-300 hover:underline">Back</button>
      </div>
    );
  }
  if (!detail) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-400">
        <Loader2 className="mr-2 h-5 w-5 animate-spin" /> Loading interview…
      </div>
    );
  }

  if (role === "candidate" && !detail.recording_consent) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950 p-6">
        <div className="max-w-lg space-y-4 rounded-2xl border border-slate-800 bg-slate-900 p-8 text-slate-300">
          <Shield className="h-8 w-8 text-indigo-400" />
          <h1 className="text-xl font-bold text-white">Before your interview</h1>
          <p className="text-sm leading-relaxed">
            This interview uses your camera and microphone. Video goes directly between you and your interviewer. Your spoken answers are
            transcribed to text and stored with your exam so a reviewer can assess them; the audio itself is not kept.
          </p>
          <p className="text-sm text-slate-400">Exam: {detail.exam_title}</p>
          <button onClick={() => void giveConsent()} className="w-full rounded-xl bg-indigo-600 py-2.5 text-sm font-bold text-white hover:bg-indigo-700">
            I agree — join the interview
          </button>
        </div>
      </div>
    );
  }

  const statusText =
    detail.status === "COMPLETED" ? "Interview ended" :
    link === "connected" ? "Connected" :
    link === "connecting" ? "Connecting…" :
    link === "replaced" ? "Opened in another tab" :
    role === "interviewer" ? "Waiting for the candidate" : "Waiting for the interviewer";

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-slate-950 text-slate-200">
      <header className="flex items-center justify-between border-b border-slate-800 bg-slate-900 px-6 py-3">
        <div className="flex items-center gap-3">
          <Shield className="h-5 w-5 text-indigo-400" />
          <div>
            <h1 className="text-sm font-bold text-white">Live Technical Interview</h1>
            <p className="text-xs text-slate-400">
              {detail.exam_title}{role === "interviewer" && detail.candidate_name ? ` · ${detail.candidate_name}` : ""}
            </p>
          </div>
        </div>
        <span className={`rounded-full px-3 py-1 text-xs font-semibold ${link === "connected" ? "bg-emerald-500/15 text-emerald-300" : "bg-slate-800 text-slate-300"}`}>
          {statusText}
        </span>
      </header>

      <div className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[1fr_380px]">
        <main className="relative flex min-h-[360px] items-center justify-center bg-black">
          <video ref={remoteVideo} autoPlay playsInline className="h-full w-full object-contain" />
          {link !== "connected" && (
            <div className="absolute inset-0 flex items-center justify-center text-sm text-slate-500">{statusText}</div>
          )}
          <video
            ref={localVideo}
            autoPlay
            playsInline
            muted
            className="absolute bottom-20 right-4 h-28 w-40 rounded-lg border border-slate-700 bg-slate-900 object-cover shadow-lg"
          />
          {mediaError && <div className="absolute top-4 rounded-lg bg-rose-500/20 px-3 py-2 text-xs text-rose-200">{mediaError}</div>}
          <div className="absolute bottom-4 flex gap-3">
            <button onClick={toggleMic} aria-label={micOn ? "Mute" : "Unmute"} className={`rounded-full p-3 ${micOn ? "bg-slate-800 hover:bg-slate-700" : "bg-rose-600"}`}>
              {micOn ? <Mic className="h-5 w-5" /> : <MicOff className="h-5 w-5" />}
            </button>
            <button onClick={toggleCam} aria-label={camOn ? "Stop camera" : "Start camera"} className={`rounded-full p-3 ${camOn ? "bg-slate-800 hover:bg-slate-700" : "bg-rose-600"}`}>
              {camOn ? <Video className="h-5 w-5" /> : <VideoOff className="h-5 w-5" />}
            </button>
            <button onClick={leave} aria-label="Leave" className="rounded-full bg-rose-600 p-3 hover:bg-rose-700">
              <PhoneOff className="h-5 w-5" />
            </button>
          </div>
        </main>

        <aside className="flex min-h-0 flex-col gap-4 overflow-y-auto border-l border-slate-800 bg-slate-900 p-4 text-sm">
          {role === "interviewer" && (
            <div className="flex gap-2">
              {detail.status !== "LIVE" && detail.status !== "COMPLETED" && (
                <button onClick={() => void setStatus("LIVE")} className="flex-1 rounded-lg bg-emerald-600 py-2 font-semibold text-white hover:bg-emerald-700">
                  Start interview
                </button>
              )}
              {detail.status !== "COMPLETED" && (
                <button onClick={() => void setStatus("COMPLETED")} className="flex-1 rounded-lg bg-slate-700 py-2 font-semibold text-white hover:bg-slate-600">
                  End interview
                </button>
              )}
            </div>
          )}

          <section>
            <h2 className="mb-2 flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-400">
              <Captions className="h-4 w-4" /> Live transcript
              {transcribing && <Loader2 className="h-3 w-3 animate-spin" />}
            </h2>
            {!detail.transcription_available ? (
              <p className="text-xs text-amber-300">Speech-to-text isn&apos;t installed on the server (requirements-ai.txt).</p>
            ) : detail.segments.length === 0 ? (
              <p className="text-xs text-slate-500">The candidate&apos;s answers appear here as they speak.</p>
            ) : (
              <ul className="space-y-2">
                {detail.segments.map((s, i) => (
                  <li key={i} className="rounded-lg bg-slate-800/60 p-2">
                    <span className="mr-2 text-[10px] text-slate-500">{new Date(s.at).toLocaleTimeString()}</span>
                    {s.text}
                  </li>
                ))}
              </ul>
            )}
          </section>

          {role === "interviewer" && (
            <>
              <section>
                <h2 className="mb-2 text-xs font-bold uppercase tracking-wider text-slate-400">Topics to cover</h2>
                <div className="flex gap-2">
                  <input
                    value={topicsText}
                    onChange={(e) => setTopicsText(e.target.value)}
                    placeholder="e.g. indexing, caching, concurrency"
                    aria-label="Topics"
                    className="flex-1 rounded-lg border border-slate-700 bg-slate-950 px-2 py-1.5 text-sm"
                  />
                  <button onClick={() => void saveTopics()} className="rounded-lg bg-slate-700 px-3 text-xs font-semibold hover:bg-slate-600">Save</button>
                </div>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {Object.entries(detail.coverage ?? {}).map(([topic, hit]) => (
                    <span key={topic} className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs ${hit ? "bg-emerald-500/15 text-emerald-300" : "bg-slate-800 text-slate-400"}`}>
                      {hit ? <CheckCircle2 className="h-3 w-3" /> : <Circle className="h-3 w-3" />} {topic}
                    </span>
                  ))}
                </div>
              </section>

              <section className="space-y-2">
                <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400">Your assessment</h2>
                {CRITERIA.map((c) => (
                  <label key={c} className="flex items-center justify-between gap-2">
                    <span>{c}</span>
                    <select
                      value={scores[c]}
                      onChange={(e) => setScores((s) => ({ ...s, [c]: Number(e.target.value) }))}
                      className="rounded-md border border-slate-700 bg-slate-950 px-2 py-1"
                    >
                      {[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>{n}</option>)}
                    </select>
                  </label>
                ))}
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={3}
                  placeholder="Notes for the review panel"
                  aria-label="Notes"
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 p-2"
                />
                <button onClick={() => void submitScore()} className="w-full rounded-lg bg-indigo-600 py-2 font-semibold text-white hover:bg-indigo-700">
                  Save score
                </button>
                {(detail.scores ?? []).map((s) => (
                  <div key={s.id} className="rounded-lg bg-slate-800/60 p-2 text-xs text-slate-300">
                    {Object.entries(s.criterion_scores).map(([k, v]) => `${k}: ${v}`).join(" · ")}
                    {s.notes && <div className="mt-1 text-slate-400">{s.notes}</div>}
                  </div>
                ))}
              </section>
            </>
          )}
        </aside>
      </div>
    </div>
  );
}
