import React, { useState, useRef, useCallback, useEffect } from "react";
import {
  ShieldCheck, ShieldAlert, ShieldX, Camera, Upload, FileText, MessageSquare,
  BarChart3, Wifi, WifiOff, ChevronRight, Send, X, Download,
  AlertTriangle, CheckCircle2, Loader2, ScanLine, Video, VideoOff,
  Building2, User, Hash, Clock, FileSearch, Sparkles,
} from "lucide-react";

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------
const API_BASE = "https://bisync-ai-compliance.onrender.com";
const TEAM_TAG = "Team CodeX99 · SIH26107";

type Role = "consumer" | "auditor";
type Lang = "en" | "hi";
type Verdict = "PASS" | "CAUTION" | "FAIL";
type Tab = "vision" | "pdf" | "chat" | "history";
type CloudStatus = "online" | "degraded" | "offline";

interface ScanResult {
  mode: string;
  product_category: string;
  matched_standard: string;
  isi_mark_detected: boolean;
  cml_number_detected: string | null;
  cml_valid_format: boolean;
  forgery_indicators: string[];
  verdict: Verdict;
  consumer_summary: string;
  auditor_summary: string;
  confidence: number;
  hash: string;
}

interface PdfClause {
  clause_no: string;
  title: string;
  requirement: string;
  status: "compliant" | "non_compliant" | "not_tested";
}

interface PdfResult {
  mode: string;
  document_type: string;
  matched_standard: string;
  clauses: PdfClause[];
  discrepancies: string[];
  overall_status: "compliant" | "non_compliant" | "partial";
  summary: string;
  hash: string;
}

interface ChatMsg {
  id: string;
  role: "user" | "assistant";
  text: string;
  sources?: string[];
}

interface AuditEntry {
  id: string;
  type: "scan" | "pdf";
  timestamp: string;
  label: string;
  standard: string;
  verdict: string;
  hash: string;
}

const COPY: Record<string, any> = {
  en: {
    appName: "BISync", tagline: "AI Compliance Copilot for Indian Standards",
    tabs: { vision: "AI Vision Inspector", pdf: "Lab PDF Parser", chat: "BIS AI Chatbot", history: "Audit History & Analytics" },
    roleConsumer: "Consumer", roleAuditor: "Industry / Auditor",
    cloud: { online: "Cloud Live", degraded: "Cache Mode", offline: "Offline" },
    dropTitle: "Drop a product photo, or use your webcam",
    dropSub: "We'll check the ISI mark, CM/L number, and product category against BIS standards.",
    browse: "Browse files", useCam: "Use webcam", capture: "Capture frame", stopCam: "Stop camera",
    scanning: "Scanning against bis_rulebook...", scanAgain: "Scan another",
    pdfDrop: "Drop a BIS manual or lab test report (PDF)",
    pdfSub: "We'll extract clauses, compliance status, and flag discrepancies.",
    chatPlaceholder: "Ask about any Indian Standard, e.g. \"flame-retardant rules for toys\"",
    chatEmpty: "Ask BISync anything about IS standards — CM/L rules, tolerance limits, testing clauses.",
    downloadReport: "Download audit report",
    noHistory: "No scans yet. Run an inspection to see it here.",
    verdictPass: "COMPLIANT", verdictCaution: "NEEDS VERIFICATION", verdictFail: "NON-COMPLIANT",
  },
  hi: {
    appName: "BISync", tagline: "भारतीय मानकों के लिए एआई अनुपालन सहायक",
    tabs: { vision: "एआई विज़न इंस्पेक्टर", pdf: "लैब PDF पार्सर", chat: "BIS एआई चैटबॉट", history: "ऑडिट इतिहास व विश्लेषण" },
    roleConsumer: "उपभोक्ता", roleAuditor: "उद्योग / ऑडिटर",
    cloud: { online: "क्लाउड लाइव", degraded: "कैश मोड", offline: "ऑफ़लाइन" },
    dropTitle: "उत्पाद की फ़ोटो डालें, या वेबकैम का उपयोग करें",
    dropSub: "हम ISI चिह्न, CM/L नंबर और उत्पाद श्रेणी की जांच BIS मानकों के अनुसार करेंगे।",
    browse: "फ़ाइल चुनें", useCam: "वेबकैम उपयोग करें", capture: "फ़्रेम कैप्चर करें", stopCam: "कैमरा बंद करें",
    scanning: "bis_rulebook के विरुद्ध स्कैन हो रहा है...", scanAgain: "फिर से स्कैन करें",
    pdfDrop: "BIS मैनुअल या लैब रिपोर्ट (PDF) डालें",
    pdfSub: "हम क्लॉज़, अनुपालन स्थिति और विसंगतियाँ निकालेंगे।",
    chatPlaceholder: "किसी भी भारतीय मानक के बारे में पूछें",
    chatEmpty: "IS मानकों, CM/L नियमों या परीक्षण क्लॉज़ के बारे में BISync से पूछें।",
    downloadReport: "ऑडिट रिपोर्ट डाउनलोड करें",
    noHistory: "अभी तक कोई स्कैन नहीं। निरीक्षण चलाएँ।",
    verdictPass: "अनुरूप", verdictCaution: "सत्यापन आवश्यक", verdictFail: "गैर-अनुरूप",
  },
};

// ---------------------------------------------------------------------------
// Mock fallbacks (demo resilience)
// ---------------------------------------------------------------------------
const MOCK_SCAN: ScanResult = {
  mode: "mock_fallback",
  product_category: "Two-Wheeler Helmet",
  matched_standard: "IS 4151",
  isi_mark_detected: true,
  cml_number_detected: "6543210",
  cml_valid_format: true,
  forgery_indicators: ["Slight font mismatch in CM/L stamp region"],
  verdict: "CAUTION",
  consumer_summary: "The ISI mark looks mostly genuine, but the certification number's font is slightly off. Verify the CM/L number on the BIS CARE portal before trusting this product.",
  auditor_summary: "CM/L OCR confidence 62% — cross-check against the BIS Licence Database. Strap anchorage clause 7.3 not fully visible in frame.",
  confidence: 0.62,
  hash: "a83f9c21e0b7",
};

const MOCK_PDF: PdfResult = {
  mode: "mock_fallback",
  document_type: "lab_report",
  matched_standard: "IS 13250",
  clauses: [
    { clause_no: "6.2", title: "Insulation resistance", requirement: "> 2 MΩ at 500V DC", status: "compliant" },
    { clause_no: "7.4", title: "Thermal cut-off", requirement: "Trips below 95°C", status: "not_tested" },
    { clause_no: "8.1", title: "Short-circuit protection", requirement: "Auto-disconnect within 2s", status: "compliant" },
  ],
  discrepancies: ["Thermal cut-off test result missing from report"],
  overall_status: "partial",
  summary: "The charger largely meets IS 13250 insulation requirements, but the thermal cut-off test wasn't documented and should be re-submitted before certification.",
  hash: "f120bc44d9e1",
};

const MOCK_CHAT_REPLIES: Record<string, string> = {
  default: "Based on IS 9873, children's toys must pass flammability testing (materials shouldn't burn faster than 30mm/second) and small-parts choke-hazard cylinder tests. I'm running on cached data right now — live AI will resume shortly.",
};

// ---------------------------------------------------------------------------
// API helper
// ---------------------------------------------------------------------------
async function apiCall<T>(path: string, options: RequestInit, mock: T, timeoutMs = 12000): Promise<{ data: T; live: boolean }> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${API_BASE}${path}`, { ...options, signal: controller.signal });
    clearTimeout(timer);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const json = await res.json();
    return { data: json as T, live: json?.mode === "live" };
  } catch (e) {
    clearTimeout(timer);
    return { data: mock, live: false };
  }
}

// ---------------------------------------------------------------------------
// Small building blocks
// ---------------------------------------------------------------------------
function VerdictBadge({ verdict, t }: { verdict: Verdict; t: any }) {
  const map = {
    PASS: { icon: ShieldCheck, cls: "text-emerald-400 border-emerald-400/40 bg-emerald-400/10", label: t.verdictPass },
    CAUTION: { icon: ShieldAlert, cls: "text-amber-400 border-amber-400/40 bg-amber-400/10", label: t.verdictCaution },
    FAIL: { icon: ShieldX, cls: "text-rose-400 border-rose-400/40 bg-rose-400/10", label: t.verdictFail },
  }[verdict];
  const Icon = map.icon;
  return (
    <div className={`inline-flex items-center gap-2 rounded-full border px-4 py-1.5 text-sm font-medium ${map.cls}`}>
      <Icon size={16} />
      {map.label}
    </div>
  );
}

function ConfidenceRing({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const circumference = 2 * Math.PI * 34;
  const offset = circumference * (1 - value);
  const color = value > 0.75 ? "#34d399" : value > 0.45 ? "#fbbf24" : "#fb7185";
  return (
    <div className="relative h-24 w-24 shrink-0">
      <svg viewBox="0 0 80 80" className="h-24 w-24 -rotate-90">
        <circle cx="40" cy="40" r="34" fill="none" stroke="rgba(148,163,184,0.15)" strokeWidth="6" />
        <circle
          cx="40" cy="40" r="34" fill="none" stroke={color} strokeWidth="6" strokeLinecap="round"
          strokeDasharray={circumference} strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 0.8s ease, stroke 0.8s ease", filter: `drop-shadow(0 0 6px ${color}66)` }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-lg font-semibold text-slate-100">{pct}%</span>
        <span className="text-[10px] uppercase tracking-wide text-slate-500">conf.</span>
      </div>
    </div>
  );
}

function GlassCard({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`rounded-2xl border border-slate-700/50 bg-slate-800/40 backdrop-blur-xl shadow-[0_8px_30px_rgba(0,0,0,0.35)] ${className}`}>
      {children}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Vision Inspector Tab
// ---------------------------------------------------------------------------
function VisionInspector({ role, lang, t, onLogged }: { role: Role; lang: Lang; t: any; onLogged: (e: AuditEntry) => void }) {
  const [preview, setPreview] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [scanning, setScanning] = useState(false);
  const [result, setResult] = useState<ScanResult | null>(null);
  const [liveMode, setLiveMode] = useState(true);
  const [camActive, setCamActive] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFile = (f: File) => {
    setFile(f);
    setPreview(URL.createObjectURL(f));
    setResult(null);
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0]);
  };

  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
      streamRef.current = stream;
      if (videoRef.current) videoRef.current.srcObject = stream;
      setCamActive(true);
    } catch {
      setCamActive(false);
    }
  };

  const stopCamera = () => {
    streamRef.current?.getTracks().forEach((tr) => tr.stop());
    setCamActive(false);
  };

  const captureFrame = () => {
    if (!videoRef.current) return;
    const canvas = document.createElement("canvas");
    canvas.width = videoRef.current.videoWidth;
    canvas.height = videoRef.current.videoHeight;
    canvas.getContext("2d")?.drawImage(videoRef.current, 0, 0);
    canvas.toBlob((blob) => {
      if (blob) {
        const f = new File([blob], "webcam-capture.jpg", { type: "image/jpeg" });
        handleFile(f);
        stopCamera();
      }
    }, "image/jpeg", 0.92);
  };

  const runScan = async () => {
    if (!file) return;
    setScanning(true);
    setResult(null);
    const form = new FormData();
    form.append("file", file);
    form.append("role", role);
    form.append("language", lang);
    const { data, live } = await apiCall<ScanResult>("/scan-image", { method: "POST", body: form }, MOCK_SCAN);
    setLiveMode(live);
    setResult(data);
    setScanning(false);
    onLogged({
      id: data.hash, type: "scan", timestamp: new Date().toISOString(),
      label: data.product_category, standard: data.matched_standard, verdict: data.verdict, hash: data.hash,
    });
  };

  const reset = () => { setFile(null); setPreview(null); setResult(null); };

  return (
    <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1.1fr_0.9fr]">
      <GlassCard className="p-6">
        {!preview && !camActive && (
          <div
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={onDrop}
            className={`flex h-96 flex-col items-center justify-center gap-4 rounded-xl border-2 border-dashed transition-colors ${dragOver ? "border-cyan-400 bg-cyan-400/5" : "border-slate-600"}`}
          >
            <div className="rounded-full bg-slate-700/50 p-4">
              <ScanLine className="text-cyan-400" size={32} />
            </div>
            <p className="text-center text-slate-200 font-medium">{t.dropTitle}</p>
            <p className="max-w-xs text-center text-sm text-slate-500">{t.dropSub}</p>
            <div className="flex gap-3">
              <button onClick={() => fileInputRef.current?.click()} className="flex items-center gap-2 rounded-lg bg-cyan-500/90 px-4 py-2 text-sm font-medium text-slate-950 hover:bg-cyan-400 transition-colors">
                <Upload size={16} /> {t.browse}
              </button>
              <button onClick={startCamera} className="flex items-center gap-2 rounded-lg border border-slate-600 px-4 py-2 text-sm font-medium text-slate-200 hover:border-slate-400 transition-colors">
                <Video size={16} /> {t.useCam}
              </button>
            </div>
            <input ref={fileInputRef} type="file" accept="image/*" className="hidden" onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])} />
          </div>
        )}

        {camActive && (
          <div className="relative h-96 overflow-hidden rounded-xl bg-black">
            <video ref={videoRef} autoPlay playsInline className="h-full w-full object-cover" />
            <div className="pointer-events-none absolute inset-8 rounded-lg border-2 border-cyan-400/60" />
            <div className="absolute bottom-4 left-1/2 flex -translate-x-1/2 gap-3">
              <button onClick={captureFrame} className="flex items-center gap-2 rounded-lg bg-cyan-500 px-4 py-2 text-sm font-semibold text-slate-950">
                <Camera size={16} /> {t.capture}
              </button>
              <button onClick={stopCamera} className="flex items-center gap-2 rounded-lg bg-slate-800/80 px-4 py-2 text-sm text-slate-200">
                <VideoOff size={16} /> {t.stopCam}
              </button>
            </div>
          </div>
        )}

        {preview && (
          <div className="relative h-96 overflow-hidden rounded-xl bg-black">
            <img src={preview} alt="scan target" className="h-full w-full object-contain" />
            {scanning && (
              <div className="absolute inset-0 bg-slate-950/40">
                <div className="absolute inset-x-0 h-1 bg-cyan-400/80 shadow-[0_0_20px_4px_rgba(34,211,238,0.6)] animate-[scanline_1.8s_ease-in-out_infinite]" />
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="flex items-center gap-2 rounded-full bg-slate-950/70 px-4 py-2 text-sm text-cyan-300">
                    <Loader2 className="animate-spin" size={16} /> {t.scanning}
                  </div>
                </div>
              </div>
            )}
            <button onClick={reset} className="absolute right-3 top-3 rounded-full bg-slate-950/70 p-1.5 text-slate-300 hover:text-white">
              <X size={16} />
            </button>
          </div>
        )}

        {preview && !result && !scanning && (
          <button onClick={runScan} className="mt-4 w-full rounded-lg bg-gradient-to-r from-cyan-500 to-blue-500 py-3 text-sm font-semibold text-slate-950 hover:opacity-90 transition-opacity">
            Run compliance scan
          </button>
        )}
        {result && (
          <button onClick={reset} className="mt-4 w-full rounded-lg border border-slate-600 py-2.5 text-sm text-slate-300 hover:border-slate-400">
            {t.scanAgain}
          </button>
        )}

        <style>{`@keyframes scanline { 0% { top: 0%; } 50% { top: 96%; } 100% { top: 0%; } }`}</style>
      </GlassCard>

      <GlassCard className="p-6">
        {!result ? (
          <div className="flex h-full min-h-[24rem] flex-col items-center justify-center gap-3 text-slate-500">
            <FileSearch size={32} />
            <p className="text-sm">Verdict and clause mapping will appear here.</p>
          </div>
        ) : (
          <div className="flex flex-col gap-5">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">{result.matched_standard}</p>
                <h3 className="mt-1 text-xl font-semibold text-slate-100">{result.product_category}</h3>
              </div>
              <ConfidenceRing value={result.confidence} />
            </div>

            <VerdictBadge verdict={result.verdict} t={t} />

            {!liveMode && (
              <div className="flex items-center gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-300">
                <AlertTriangle size={14} /> Showing cached sample data — live API temporarily unreachable.
              </div>
            )}

            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-lg border border-slate-700/60 bg-slate-900/40 p-3">
                <p className="text-xs text-slate-500">ISI Mark</p>
                <p className={`mt-1 flex items-center gap-1.5 text-sm font-medium ${result.isi_mark_detected ? "text-emerald-400" : "text-rose-400"}`}>
                  {result.isi_mark_detected ? <CheckCircle2 size={14} /> : <ShieldX size={14} />}
                  {result.isi_mark_detected ? "Detected" : "Not found"}
                </p>
              </div>
              <div className="rounded-lg border border-slate-700/60 bg-slate-900/40 p-3">
                <p className="text-xs text-slate-500">CM/L Number</p>
                <p className="mt-1 flex items-center gap-1.5 text-sm font-medium text-slate-200">
                  <Hash size={14} /> {result.cml_number_detected ?? "—"}
                </p>
              </div>
            </div>

            {result.forgery_indicators.length > 0 && (
              <div className="rounded-lg border border-slate-700/60 bg-slate-900/40 p-3">
                <p className="mb-2 text-xs uppercase tracking-wide text-slate-500">Forgery indicators</p>
                <ul className="space-y-1.5">
                  {result.forgery_indicators.map((f, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
                      <AlertTriangle className="mt-0.5 shrink-0 text-amber-400" size={13} /> {f}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div className="rounded-lg bg-slate-900/40 p-3">
              <p className="text-xs uppercase tracking-wide text-slate-500 mb-1">{role === "consumer" ? "Plain-English verdict" : "Auditor notes"}</p>
              <p className="text-sm leading-relaxed text-slate-300">{role === "consumer" ? result.consumer_summary : result.auditor_summary}</p>
            </div>

            <button className="flex items-center justify-center gap-2 rounded-lg border border-slate-600 py-2.5 text-sm text-slate-300 hover:border-cyan-400 hover:text-cyan-300 transition-colors">
              <Download size={15} /> {t.downloadReport}
            </button>
          </div>
        )}
      </GlassCard>
    </div>
  );
}

// ---------------------------------------------------------------------------
// PDF Parser Tab
// ---------------------------------------------------------------------------
function PdfParser({ role, lang, t, onLogged }: { role: Role; lang: Lang; t: any; onLogged: (e: AuditEntry) => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [parsing, setParsing] = useState(false);
  const [result, setResult] = useState<PdfResult | null>(null);
  const [liveMode, setLiveMode] = useState(true);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const runParse = async (f: File) => {
    setFile(f);
    setParsing(true);
    setResult(null);
    const form = new FormData();
    form.append("file", f);
    form.append("role", role);
    form.append("language", lang);
    const { data, live } = await apiCall<PdfResult>("/parse-pdf", { method: "POST", body: form }, MOCK_PDF);
    setLiveMode(live);
    setResult(data);
    setParsing(false);
    onLogged({ id: data.hash, type: "pdf", timestamp: new Date().toISOString(), label: f.name, standard: data.matched_standard, verdict: data.overall_status, hash: data.hash });
  };

  const statusColor: Record<string, string> = { compliant: "text-emerald-400", non_compliant: "text-rose-400", not_tested: "text-slate-500", partial: "text-amber-400" };

  return (
    <div className="grid grid-cols-1 gap-6 xl:grid-cols-[0.8fr_1.2fr]">
      <GlassCard className="p-6">
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => { e.preventDefault(); setDragOver(false); if (e.dataTransfer.files[0]) runParse(e.dataTransfer.files[0]); }}
          className={`flex h-64 flex-col items-center justify-center gap-4 rounded-xl border-2 border-dashed transition-colors ${dragOver ? "border-cyan-400 bg-cyan-400/5" : "border-slate-600"}`}
        >
          <div className="rounded-full bg-slate-700/50 p-4"><FileText className="text-cyan-400" size={28} /></div>
          <p className="text-center text-slate-200 font-medium text-sm">{t.pdfDrop}</p>
          <p className="max-w-xs text-center text-xs text-slate-500">{t.pdfSub}</p>
          <button onClick={() => inputRef.current?.click()} className="flex items-center gap-2 rounded-lg bg-cyan-500/90 px-4 py-2 text-sm font-medium text-slate-950 hover:bg-cyan-400">
            <Upload size={15} /> {t.browse}
          </button>
          <input ref={inputRef} type="file" accept="application/pdf" className="hidden" onChange={(e) => e.target.files?.[0] && runParse(e.target.files[0])} />
        </div>
        {file && (
          <div className="mt-4 flex items-center gap-2 rounded-lg bg-slate-900/40 px-3 py-2 text-sm text-slate-300">
            <FileText size={14} className="text-cyan-400 shrink-0" />
            <span className="truncate">{file.name}</span>
            {parsing && <Loader2 className="ml-auto animate-spin text-cyan-400" size={14} />}
          </div>
        )}
      </GlassCard>

      <GlassCard className="p-6">
        {!result ? (
          <div className="flex h-full min-h-[20rem] flex-col items-center justify-center gap-3 text-slate-500">
            <Sparkles size={28} />
            <p className="text-sm">Extracted clauses will appear here.</p>
          </div>
        ) : (
          <div className="flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">{result.matched_standard} · {result.document_type.replace("_", " ")}</p>
                <p className={`mt-1 text-sm font-semibold ${statusColor[result.overall_status]}`}>
                  Overall: {result.overall_status.replace("_", " ")}
                </p>
              </div>
            </div>
            {!liveMode && (
              <div className="flex items-center gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-300">
                <AlertTriangle size={14} /> Showing cached sample data — live API temporarily unreachable.
              </div>
            )}
            <div className="overflow-hidden rounded-lg border border-slate-700/60">
              <table className="w-full text-sm">
                <thead className="bg-slate-900/60 text-xs uppercase text-slate-500">
                  <tr><th className="px-3 py-2 text-left">Clause</th><th className="px-3 py-2 text-left">Requirement</th><th className="px-3 py-2 text-left">Status</th></tr>
                </thead>
                <tbody>
                  {result.clauses.map((c, i) => (
                    <tr key={i} className="border-t border-slate-700/40">
                      <td className="px-3 py-2 align-top text-slate-300">{c.clause_no}<br /><span className="text-xs text-slate-500">{c.title}</span></td>
                      <td className="px-3 py-2 align-top text-slate-400">{c.requirement}</td>
                      <td className={`px-3 py-2 align-top font-medium ${statusColor[c.status]}`}>{c.status.replace("_", " ")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {result.discrepancies.length > 0 && (
              <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3">
                <p className="mb-1.5 text-xs uppercase tracking-wide text-amber-400/80">Discrepancies</p>
                {result.discrepancies.map((d, i) => (
                  <p key={i} className="flex items-start gap-2 text-sm text-slate-300"><AlertTriangle size={13} className="mt-0.5 shrink-0 text-amber-400" />{d}</p>
                ))}
              </div>
            )}
            <p className="text-sm leading-relaxed text-slate-300">{result.summary}</p>
            <button className="flex items-center justify-center gap-2 rounded-lg border border-slate-600 py-2.5 text-sm text-slate-300 hover:border-cyan-400 hover:text-cyan-300">
              <Download size={15} /> {t.downloadReport}
            </button>
          </div>
        )}
      </GlassCard>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Chatbot Tab
// ---------------------------------------------------------------------------
function Chatbot({ role, lang, t }: { role: Role; lang: Lang; t: any }) {
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [input, setInput] = useState("");
  const [thinking, setThinking] = useState(false);
  const [liveMode, setLiveMode] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, thinking]);

  const send = async () => {
    const text = input.trim();
    if (!text) return;
    const userMsg: ChatMsg = { id: crypto.randomUUID(), role: "user", text };
    setMessages((m) => [...m, userMsg]);
    setInput("");
    setThinking(true);

    const mock = { mode: "mock_fallback", answer: MOCK_CHAT_REPLIES.default, sources: ["IS 9873"] };
    const { data, live } = await apiCall<typeof mock>(
      "/chat",
      { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message: text, language: lang, role }) },
      mock
    );
    setLiveMode(live);
    setMessages((m) => [...m, { id: crypto.randomUUID(), role: "assistant", text: data.answer, sources: data.sources }]);
    setThinking(false);
  };

  return (
    <GlassCard className="flex h-[70vh] flex-col">
      <div className="flex items-center justify-between border-b border-slate-700/50 px-6 py-4">
        <div className="flex items-center gap-2">
          <div className="rounded-full bg-cyan-500/15 p-2"><MessageSquare className="text-cyan-400" size={18} /></div>
          <div>
            <p className="text-sm font-medium text-slate-100">BIS AI Chatbot</p>
            <p className="text-xs text-slate-500">RAG over bis_rulebook · Gemini</p>
          </div>
        </div>
        {!liveMode && messages.length > 0 && (
          <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-2.5 py-1 text-xs text-amber-300">Cache mode</span>
        )}
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto px-6 py-5">
        {messages.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center gap-2 text-center text-slate-500">
            <MessageSquare size={28} />
            <p className="max-w-sm text-sm">{t.chatEmpty}</p>
          </div>
        )}
        {messages.map((m) => (
          <div key={m.id} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[75%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${m.role === "user" ? "bg-cyan-500 text-slate-950" : "bg-slate-800/70 text-slate-200 border border-slate-700/50"}`}>
              {m.text}
              {m.sources && m.sources.length > 0 && (
                <p className="mt-1.5 text-xs opacity-60">Sources: {m.sources.join(", ")}</p>
              )}
            </div>
          </div>
        ))}
        {thinking && (
          <div className="flex justify-start">
            <div className="flex items-center gap-2 rounded-2xl border border-slate-700/50 bg-slate-800/70 px-4 py-2.5 text-sm text-slate-400">
              <Loader2 className="animate-spin" size={14} /> thinking...
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="border-t border-slate-700/50 p-4">
        <div className="flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-900/60 px-3 py-2 focus-within:border-cyan-400/60">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send()}
            placeholder={t.chatPlaceholder}
            className="flex-1 bg-transparent text-sm text-slate-200 placeholder-slate-500 outline-none"
          />
          <button onClick={send} disabled={!input.trim()} className="rounded-lg bg-cyan-500 p-2 text-slate-950 disabled:opacity-30">
            <Send size={15} />
          </button>
        </div>
      </div>
    </GlassCard>
  );
}

// ---------------------------------------------------------------------------
// Audit History Tab
// ---------------------------------------------------------------------------
function AuditHistory({ entries, t }: { entries: AuditEntry[]; t: any }) {
  const passCount = entries.filter((e) => e.verdict === "PASS" || e.verdict === "compliant").length;
  const cautionCount = entries.filter((e) => e.verdict === "CAUTION" || e.verdict === "partial").length;
  const failCount = entries.filter((e) => e.verdict === "FAIL" || e.verdict === "non_compliant").length;

  const stats = [
    { label: "Total Inspections", value: entries.length, icon: BarChart3, color: "text-cyan-400" },
    { label: "Compliant", value: passCount, icon: CheckCircle2, color: "text-emerald-400" },
    { label: "Needs Verification", value: cautionCount, icon: ShieldAlert, color: "text-amber-400" },
    { label: "Non-Compliant", value: failCount, icon: ShieldX, color: "text-rose-400" },
  ];

  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {stats.map((s) => (
          <GlassCard key={s.label} className="p-5">
            <s.icon className={s.color} size={20} />
            <p className="mt-3 text-2xl font-semibold text-slate-100">{s.value}</p>
            <p className="text-xs text-slate-500">{s.label}</p>
          </GlassCard>
        ))}
      </div>

      <GlassCard className="p-6">
        <p className="mb-4 text-sm font-medium text-slate-200">Recent activity</p>
        {entries.length === 0 ? (
          <div className="flex flex-col items-center gap-2 py-12 text-slate-500">
            <Clock size={26} />
            <p className="text-sm">{t.noHistory}</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-700/40">
            {entries.slice().reverse().map((e) => (
              <div key={e.id} className="flex items-center justify-between py-3">
                <div className="flex items-center gap-3">
                  <div className="rounded-lg bg-slate-900/60 p-2">
                    {e.type === "scan" ? <Camera size={15} className="text-cyan-400" /> : <FileText size={15} className="text-cyan-400" />}
                  </div>
                  <div>
                    <p className="text-sm text-slate-200">{e.label}</p>
                    <p className="text-xs text-slate-500">{e.standard} · {new Date(e.timestamp).toLocaleString()}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="rounded-full border border-slate-600 px-2.5 py-1 text-xs text-slate-400">{e.verdict}</span>
                  <span className="hidden font-mono text-xs text-slate-600 sm:inline">#{e.hash}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </GlassCard>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Shell: Sidebar + Header
// ---------------------------------------------------------------------------
function Sidebar({ tab, setTab, t }: { tab: Tab; setTab: (t: Tab) => void; t: any }) {
  const items: { id: Tab; icon: React.ElementType; label: string }[] = [
    { id: "vision", icon: Camera, label: t.tabs.vision },
    { id: "pdf", icon: FileText, label: t.tabs.pdf },
    { id: "chat", icon: MessageSquare, label: t.tabs.chat },
    { id: "history", icon: BarChart3, label: t.tabs.history },
  ];
  return (
    <aside className="flex w-64 shrink-0 flex-col border-r border-slate-800 bg-slate-950/60 px-4 py-6">
      <div className="mb-8 flex items-center gap-3 px-2">
        <img 
          src="https://i.ibb.co/ymTht2pS/20260922-202442.png" 
          alt="BISync Logo" 
          className="h-10 w-10 rounded-xl object-cover shadow-sm border border-slate-700 bg-white"
        />
        <div>
          <p className="text-sm font-semibold text-slate-100">BISync</p>
          <p className="text-[11px] text-slate-500">{TEAM_TAG}</p>
        </div>
      </div>
      <nav className="flex flex-col gap-1">
        {items.map((it) => (
          <button
            key={it.id}
            onClick={() => setTab(it.id)}
            className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors ${
              tab === it.id ? "bg-cyan-500/15 text-cyan-300 border border-cyan-500/30" : "text-slate-400 hover:bg-slate-800/60 hover:text-slate-200"
            }`}
          >
            <it.icon size={17} />
            {it.label}
            {tab === it.id && <ChevronRight size={14} className="ml-auto" />}
          </button>
        ))}
      </nav>
      <div className="mt-auto rounded-xl border border-slate-800 bg-slate-900/50 p-4">
        <p className="text-xs text-slate-500 leading-relaxed">Guarding ₹1L+ crore in economic loss from counterfeit ISI marks — one scan at a time.</p>
      </div>
    </aside>
  );
}

function Header({ role, setRole, lang, setLang, cloud, t }: {
  role: Role; setRole: (r: Role) => void; lang: Lang; setLang: (l: Lang) => void; cloud: CloudStatus; t: any;
}) {
  const cloudCfg = {
    online: { icon: Wifi, cls: "text-emerald-400", label: t.cloud.online },
    degraded: { icon: Wifi, cls: "text-amber-400", label: t.cloud.degraded },
    offline: { icon: WifiOff, cls: "text-rose-400", label: t.cloud.offline },
  }[cloud];
  const CloudIcon = cloudCfg.icon;

  return (
    <header className="flex items-center justify-between border-b border-slate-800 bg-slate-950/40 px-8 py-4">
      <div>
        <h1 className="text-lg font-semibold text-slate-100">{t.appName}</h1>
        <p className="text-xs text-slate-500">{t.tagline}</p>
      </div>

      <div className="flex items-center gap-5">
        <div className={`flex items-center gap-1.5 text-xs ${cloudCfg.cls}`}>
          <CloudIcon size={14} /> {cloudCfg.label}
        </div>

        <div className="flex rounded-lg border border-slate-700 bg-slate-900/60 p-0.5 text-xs">
          {(["en", "hi"] as Lang[]).map((l) => (
            <button key={l} onClick={() => setLang(l)} className={`rounded-md px-2.5 py-1.5 transition-colors ${lang === l ? "bg-cyan-500 text-slate-950" : "text-slate-400"}`}>
              {l.toUpperCase()}
            </button>
          ))}
        </div>

        <div className="flex rounded-lg border border-slate-700 bg-slate-900/60 p-0.5 text-xs">
          <button onClick={() => setRole("consumer")} className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 transition-colors ${role === "consumer" ? "bg-cyan-500 text-slate-950" : "text-slate-400"}`}>
            <User size={13} /> {t.roleConsumer}
          </button>
          <button onClick={() => setRole("auditor")} className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 transition-colors ${role === "auditor" ? "bg-cyan-500 text-slate-950" : "text-slate-400"}`}>
            <Building2 size={13} /> {t.roleAuditor}
          </button>
        </div>
      </div>
    </header>
  );
}

// ---------------------------------------------------------------------------
// Root App
// ---------------------------------------------------------------------------
export default function App() {
  const [tab, setTab] = useState<Tab>("vision");
  const [role, setRole] = useState<Role>("consumer");
  const [lang, setLang] = useState<Lang>("en");
  const [cloud, setCloud] = useState<CloudStatus>("online");
  const [history, setHistory] = useState<AuditEntry[]>([]);

  const t = COPY[lang];

  useEffect(() => {
    let mounted = true;
    const ping = async () => {
      try {
        const res = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(6000) });
        if (!mounted) return;
        setCloud(res.ok ? "online" : "degraded");
      } catch {
        if (mounted) setCloud("offline");
      }
    };
    ping();
    const interval = setInterval(ping, 30000);
    return () => { mounted = false; clearInterval(interval); };
  }, []);

  const logEntry = useCallback((e: AuditEntry) => setHistory((h) => [...h, e]), []);

  return (
    <div className="min-w-full min-h-screen bg-[#0a0f1a] text-slate-200 flex" style={{
      backgroundImage: "radial-gradient(circle at 15% 0%, rgba(34,211,238,0.06), transparent 40%), radial-gradient(circle at 85% 100%, rgba(59,130,246,0.06), transparent 40%)",
    }}>
      <Sidebar tab={tab} setTab={setTab} t={t} />
      <div className="flex min-w-0 flex-1 flex-col">
        <Header role={role} setRole={setRole} lang={lang} setLang={setLang} cloud={cloud} t={t} />
        <main className="flex-1 overflow-y-auto px-8 py-8">
          {tab === "vision" && <VisionInspector role={role} lang={lang} t={t} onLogged={logEntry} />}
          {tab === "pdf" && <PdfParser role={role} lang={lang} t={t} onLogged={logEntry} />}
          {tab === "chat" && <Chatbot role={role} lang={lang} t={t} />}
          {tab === "history" && <AuditHistory entries={history} t={t} />}
        </main>
      </div>
    </div>
  );
}