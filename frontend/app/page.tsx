"use client";

import { useState, useRef, useEffect, useMemo } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Check, ChevronDown, ChevronRight, Loader2, Mic, Paperclip, Send, Square, X } from "lucide-react";
import { useApi, BACKEND } from "./lib/api";
import { BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";

type TableArtifact = { artifact_type: "table"; columns: string[]; rows: unknown[][]; title?: string };
type ChartArtifact = { artifact_type: "chart"; chart_type: "bar" | "line" | "pie"; title: string; x_key?: string; series?: { key: string; label: string }[]; data: Record<string, unknown>[] };
type ImageArtifact = { artifact_type: "image"; content: string; columns?: string[]; rows?: unknown[][]; title?: string };
type PoLine = { product: string; qty: number; unit_price: number; total: number };
type PoData = { po_number?: string; date?: string; vendor?: { name: string }; lines?: PoLine[]; subtotal?: number; tax?: number; total?: number };
type PdfArtifact = { artifact_type: "pdf"; content: string; title?: string; data?: PoData };
type Artifact = TableArtifact | ChartArtifact | ImageArtifact | PdfArtifact;
type Message = { role: "user" | "assistant"; content: string; steps?: string[]; artifacts?: Artifact[] };
type Tab = { id: string; label: string; messages: Message[] };
type LogEntry = { content: string; timestamp: string };
type McpServer = { name: string; transport: string; status: "ok" | "error" };
type PendingAction = { action_id: string; summary: string; details?: Record<string, unknown>; agent_name: string; timestamp: string };

// const BACKEND = "http://localhost:8000";

function newTab(label = "New Chat"): Tab {
  return { id: crypto.randomUUID(), label, messages: [] };
}

function renderInline(line: string) {
  const parts = line.split(/(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) return <strong key={i}>{part.slice(2, -2)}</strong>;
    if (part.startsWith("*") && part.endsWith("*")) return <em key={i}>{part.slice(1, -1)}</em>;
    if (part.startsWith("`") && part.endsWith("`")) return <code key={i} className="bg-gray-700 px-1 rounded text-xs font-mono">{part.slice(1, -1)}</code>;
    return <span key={i}>{part}</span>;
  });
}

function renderMarkdown(text: string) {
  return text.split("\n").map((line, i) => (
    <span key={i}>{i > 0 && <br />}{renderInline(line)}</span>
  ));
}


const CHART_COLORS = ["#6366f1", "#22d3ee", "#f59e0b", "#10b981", "#f43f5e", "#a78bfa"];

function ChartWidget({ artifact }: { artifact: ChartArtifact }) {
  const { chart_type, data, x_key, series } = artifact;
  if (chart_type === "pie") {
    return (
      <ResponsiveContainer width="100%" height={280}>
        <PieChart>
          <Pie data={data} dataKey="value" nameKey="name" cx="50%" cy="45%" outerRadius={90} label={({ percent }) => `${(percent * 100).toFixed(0)}%`} labelLine={false}>
            {data.map((_, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
          </Pie>
          <Tooltip />
          <Legend verticalAlign="bottom" height={36} />
        </PieChart>
      </ResponsiveContainer>
    );
  }
  if (chart_type === "line") {
    return (
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis dataKey={x_key} tick={{ fontSize: 10, fill: "#9ca3af" }} />
          <YAxis tick={{ fontSize: 10, fill: "#9ca3af" }} />
          <Tooltip contentStyle={{ backgroundColor: "#1f2937", border: "none", fontSize: 11 }} />
          {series && series.length > 0 && <Legend wrapperStyle={{ fontSize: 11 }} />}
          {(series ?? []).map((s, i) => <Line key={s.key} type="monotone" dataKey={s.key} name={s.label} stroke={CHART_COLORS[i % CHART_COLORS.length]} dot={false} />)}
        </LineChart>
      </ResponsiveContainer>
    );
  }
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
        <XAxis dataKey={x_key} tick={{ fontSize: 10, fill: "#9ca3af" }} />
        <YAxis tick={{ fontSize: 10, fill: "#9ca3af" }} />
        <Tooltip contentStyle={{ backgroundColor: "#1f2937", border: "none", fontSize: 11 }} />
        {series && series.length > 0 && <Legend wrapperStyle={{ fontSize: 11 }} />}
        {(series ?? []).map((s, i) => <Bar key={s.key} dataKey={s.key} name={s.label} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
      </BarChart>
    </ResponsiveContainer>
  );
}

export default function Page() {
  const router = useRouter();
  const { apiFetch, authHeader } = useApi();
  const [tabs, setTabs] = useState<Tab[]>([]);
  const [activeTabId, setActiveTabId] = useState<string>("");
  const [closedTabs, setClosedTabs] = useState<Tab[]>([]);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [input, setInput] = useState("");
  const [attachedFile, setAttachedFile] = useState<File | null>(null);
  const [recording, setRecording] = useState(false);
  const [liveTranscript, setLiveTranscript] = useState("");
  const [loading, setLoading] = useState(false);
  const speechRecognitionRef = useRef<SpeechRecognition | null>(null);
  const [pendingSteps, setPendingSteps] = useState<string[]>([]);
  const [expandedSteps, setExpandedSteps] = useState<Set<number>>(new Set());
  const [mcpServers, setMcpServers] = useState<McpServer[]>([]);
  const [refreshInterval, setRefreshInterval] = useState(10);
  const [pendingActions, setPendingActions] = useState<PendingAction[]>([]);
  const [userRole, setUserRole] = useState<string>("");

  useEffect(() => {
    if (!localStorage.getItem("access_token")) { router.replace("/login"); return; }
    setUserRole(localStorage.getItem("user_role") ?? "");

    Promise.all([
      apiFetch<{ id: string; label: string }[]>(`${BACKEND}/api/agent/sessions/`),
      apiFetch<{ id: string; label: string }[]>(`${BACKEND}/api/agent/sessions/closed/`),
    ]).then(([open, closed]) => {
      if (!open || !closed) return;
      const openTabs = open.map(s => ({ id: s.id, label: s.label, messages: [] as Message[] }));
      const closedTabList = closed.map(s => ({ id: s.id, label: s.label, messages: [] as Message[] }));
      if (openTabs.length > 0) {
        setTabs(openTabs);
        setActiveTabId(openTabs[0].id);
      } else {
        const t = newTab();
        apiFetch(`${BACKEND}/api/agent/sessions/create/`, {
          method: "POST",
          body: JSON.stringify({ id: t.id, label: t.label }),
        }).catch(() => {});
        setTabs([t]);
        setActiveTabId(t.id);
      }
      setClosedTabs(closedTabList);
    }).catch(() => {});
  }, [router]);

  // function authHeader() { ... } — moved to useApi

  async function downloadExport(type: "csv" | "pdf" | "xlsx", artifact: { columns?: string[]; rows?: unknown[][]; title?: string }) {
    const body = { format: type, columns: artifact.columns, rows: artifact.rows, title: artifact.title ?? "" };
    const res = await fetch(`${BACKEND}/api/agent/export/${type}/`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeader() },
      body: JSON.stringify(body),
    });
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${artifact.title || "export"}.${type}`;
    a.click();
    URL.revokeObjectURL(url);
  }

  // function logout() {
  //   localStorage.removeItem("access_token");
  //   localStorage.removeItem("user_role");
  //   localStorage.removeItem("username");
  //   router.replace("/login");
  // }

  const activeTab = tabs.find(t => t.id === activeTabId) ?? tabs[0];
  const messages = useMemo(() => activeTab?.messages ?? [], [activeTab]);

  function updateMessages(tabId: string, updater: (prev: Message[]) => Message[]) {
    setTabs(prev => prev.map(t => t.id === tabId ? { ...t, messages: updater(t.messages) } : t));
  }

  function addTab() {
    const t = newTab();
    apiFetch(`${BACKEND}/api/agent/sessions/create/`, {
      method: "POST",
      body: JSON.stringify({ id: t.id, label: t.label }),
    }).catch(() => {});
    setTabs(prev => [...prev, t]);
    setActiveTabId(t.id);
    setExpandedSteps(new Set());
  }

  function closeTab(id: string) {
    const closing = tabs.find(t => t.id === id);
    if (closing) {
      apiFetch(`${BACKEND}/api/agent/sessions/${id}/`, {
        method: "PATCH",
        body: JSON.stringify({ is_closed: true }),
      }).catch(() => {});
      setClosedTabs(c => [closing, ...c].slice(0, 20));
    }
    setTabs(prev => {
      const next = prev.filter(t => t.id !== id);
      if (next.length === 0) {
        const t = newTab();
        apiFetch(`${BACKEND}/api/agent/sessions/create/`, {
          method: "POST",
          body: JSON.stringify({ id: t.id, label: t.label }),
        }).catch(() => {});
        setActiveTabId(t.id);
        return [t];
      }
      if (activeTabId === id) {
        setActiveTabId(next[next.length - 1].id);
        setExpandedSteps(new Set());
      }
      return next;
    });
  }

  function restoreTab(tab: Tab) {
    apiFetch(`${BACKEND}/api/agent/sessions/${tab.id}/`, {
      method: "PATCH",
      body: JSON.stringify({ is_closed: false }),
    }).catch(() => {});
    setClosedTabs(prev => prev.filter(t => t.id !== tab.id));
    setTabs(prev => [...prev, { ...tab, messages: [] }]);
    setActiveTabId(tab.id);
    setExpandedSteps(new Set());
    setHistoryOpen(false);
  }

  function deleteClosedTab(id: string) {
    apiFetch(`${BACKEND}/api/agent/sessions/${id}/`, {
      method: "DELETE",
    }).catch(() => {});
    setClosedTabs(prev => prev.filter(t => t.id !== id));
  }

  function switchTab(id: string) {
    setActiveTabId(id);
    setExpandedSteps(new Set());
  }

  useEffect(() => {
    if (!activeTabId) return;
    apiFetch<{ role: string; content: string; artifacts: Artifact[]; steps: string[] }[]>(`${BACKEND}/api/agent/sessions/${activeTabId}/messages/`)
      .then(rows => {
        if (!rows || rows.length === 0) return;
        setTabs(prev => prev.map(t =>
          t.id === activeTabId
            ? { ...t, messages: rows.map(r => ({ role: r.role as "user" | "assistant", content: r.content, artifacts: r.artifacts, steps: r.steps })) }
            : t
        ));
      })
      .catch(() => {});
  }, [activeTabId]);

  const chatEndRef = useRef<HTMLDivElement>(null);
  const logEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, pendingSteps, liveTranscript]);
  useEffect(() => { logEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [logs]);

  useEffect(() => {
    async function fetchHealth() {
      try {
        const data = await apiFetch<McpServer[]>(`${BACKEND}/api/agent/mcp/health/`);
        if (data) setMcpServers(data);
      } catch {}
    }
    fetchHealth();
    const id = setInterval(fetchHealth, refreshInterval * 1000);
    return () => clearInterval(id);
  }, [refreshInterval]);

  useEffect(() => {
    async function fetchPending() {
      try {
        const data = await apiFetch<PendingAction[]>(`${BACKEND}/api/agent/pending/`);
        if (data) setPendingActions(data);
      } catch {}
    }
    fetchPending();
  }, []);

  function toggleSteps(index: number) {
    setExpandedSteps((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  }

  async function readStream(res: Response, tabId: string) {
    const reader = res.body!.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let localSteps: string[] = [];
    let localArtifacts: Artifact[] = [];

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const raw = line.slice(6).trim();
        if (raw === "[DONE]") break;

        const event = JSON.parse(raw);
        if (event.type === "progress") {
          localSteps = [...localSteps, event.content];
          setPendingSteps(localSteps);
          setLogs((prev) => [...prev, { content: event.content, timestamp: new Date().toLocaleTimeString() }]);
        } else if (event.type === "artifact") {
          localArtifacts = [...localArtifacts, event as Artifact];
        } else if (event.type === "pdf") {
          localArtifacts = [...localArtifacts, { artifact_type: "pdf", content: event.content, title: event.title, data: event.data } as PdfArtifact];
        } else if (event.type === "image") {
          const lastTable = [...localArtifacts].reverse().find(a => a.artifact_type === "table") as TableArtifact | undefined;
          localArtifacts = [...localArtifacts, { artifact_type: "image", content: event.content, columns: lastTable?.columns, rows: lastTable?.rows, title: lastTable?.title } as ImageArtifact];
        } else if (event.type === "confirmation") {
          setPendingActions((prev) => [
            ...prev,
            {
              action_id: event.action_id,
              summary: event.summary,
              details: event.details ?? {},
              agent_name: "",
              timestamp: new Date().toISOString(),
            },
          ]);
        } else if (event.type === "response") {
          updateMessages(tabId, prev => [...prev, { role: "assistant", content: event.content, steps: localSteps, artifacts: localArtifacts }]);
          setPendingSteps([]);
        }
      }
    }
  }

  function toggleRecording() {
    if (recording) {
      speechRecognitionRef.current?.stop();
      return;
    }
    const SR = (window as unknown as { SpeechRecognition?: typeof SpeechRecognition; webkitSpeechRecognition?: typeof SpeechRecognition }).SpeechRecognition
      ?? (window as unknown as { webkitSpeechRecognition?: typeof SpeechRecognition }).webkitSpeechRecognition;
    if (!SR) return;
    const recognition = new SR();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "en-US";
    let finalText = "";
    recognition.onresult = (e: SpeechRecognitionEvent) => {
      let interim = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        if (e.results[i].isFinal) finalText += e.results[i][0].transcript;
        else interim += e.results[i][0].transcript;
      }
      setLiveTranscript(finalText + interim);
    };
    recognition.onend = () => {
      setRecording(false);
      setLiveTranscript("");
      if (finalText.trim()) sendMessage(finalText.trim());
    };
    speechRecognitionRef.current = recognition;
    recognition.start();
    setRecording(true);
    setLiveTranscript("");
  }

  async function sendMessage(text: string, file?: File | null) {
    const tabId = activeTabId;
    let userMessage = text;
    let imageFile: { image_data: string; content_type: string; filename: string } | null = null;

    setLoading(true);
    setLogs([]);
    setPendingSteps([]);

    if (file) {
      const formData = new FormData();
      formData.append("file", file);
      const token = localStorage.getItem("access_token");
      const uploadRes = await fetch(`${BACKEND}/api/agent/upload/`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      });
      if (uploadRes.ok) {
        const uploadData = await uploadRes.json();
        if (uploadData.image_data) {
          imageFile = uploadData;
          userMessage = userMessage || `Acknowledge receipt with "Received: [brief title/description]" on one line, then "Awaiting your instructions." on the next. Keep it brief.`;
        } else {
          const task = userMessage || `Acknowledge receipt with "Received: [brief title/description]" on one line, then "Awaiting your instructions." on the next. Keep it brief. Do not display the file content.`;
          userMessage = `[File: ${file.name}]\n${uploadData.content}\n\n${task}`;
        }
      }
    }

    const isFirst = (tabs.find(t => t.id === tabId)?.messages ?? []).length === 0;
    if (isFirst) {
      const label = file ? file.name.slice(0, 22) : userMessage.slice(0, 22);
      setTabs(prev => prev.map(t => t.id === tabId ? { ...t, label } : t));
      apiFetch(`${BACKEND}/api/agent/sessions/${tabId}/`, {
        method: "PATCH",
        body: JSON.stringify({ label }),
      }).catch(() => {});
    }

    const displayContent = file
      ? `[File: ${file.name}]` + (text ? `\n\n${text}` : "")
      : userMessage;
    updateMessages(tabId, prev => [...prev, { role: "user", content: displayContent }]);

    const res = await fetch(`${BACKEND}/api/agent/chat/`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeader() },
      body: JSON.stringify({ message: userMessage, session_key: tabId, ...(imageFile ? { image_file: imageFile } : {}) }),
    });

    await readStream(res, tabId);
    setLoading(false);
  }

  async function send() {
    if ((!input.trim() && !attachedFile) || loading) return;
    const typedText = input.trim();
    const file = attachedFile;
    setInput("");
    setAttachedFile(null);
    await sendMessage(typedText, file);
  }

  async function confirm(action: PendingAction) {
    const tabId = activeTabId;
    setPendingActions((prev) => prev.filter((a) => a.action_id !== action.action_id));
    setLoading(true);
    setLogs([]);
    setPendingSteps([]);

    const res = await fetch(`${BACKEND}/api/agent/confirm/${action.action_id}/`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeader() },
      body: JSON.stringify({ session_key: tabId }),
    });

    await readStream(res, tabId);
    setLoading(false);
  }

  async function cancel(action: PendingAction) {
    const tabId = activeTabId;
    setPendingActions((prev) => prev.filter((a) => a.action_id !== action.action_id));
    await fetch(`${BACKEND}/api/agent/cancel/${action.action_id}/`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeader() },
      body: JSON.stringify({ session_key: tabId }),
    });
    updateMessages(tabId, prev => [...prev, { role: "assistant", content: "Action cancelled." }]);
  }

  return (
    <div className="flex flex-col h-full bg-gray-950 text-gray-100">
      <div className="flex items-center gap-3 px-4 py-2 border-b border-gray-800 text-xs shrink-0">
        <span className="text-gray-500 font-medium">MCP Servers</span>
        {mcpServers.map((s) => (
          <span key={s.name} className="flex items-center gap-1.5 bg-gray-800 px-2.5 py-1 rounded-full">
            <span className={`w-1.5 h-1.5 rounded-full ${s.status === "ok" ? "bg-green-400" : "bg-red-400"}`} />
            <span className="text-gray-300 capitalize">{s.name}</span>
          </span>
        ))}
        {userRole && (
          <span className="ml-auto text-xs text-gray-500 bg-gray-800 px-2.5 py-1 rounded-full capitalize">{userRole}</span>
        )}
        <div className="flex items-center gap-2 text-gray-500">
          <span>Refresh</span>
          <select
            className="bg-gray-800 text-gray-300 rounded px-2 py-0.5 outline-none"
            value={refreshInterval}
            onChange={(e) => setRefreshInterval(Number(e.target.value))}
          >
            <option value={5}>5s</option>
            <option value={10}>10s</option>
            <option value={30}>30s</option>
            <option value={60}>60s</option>
          </select>
        </div>
      </div>
      <div className="flex flex-1 overflow-hidden">
      <div className="flex flex-col flex-1 border-r border-gray-800 min-w-0">
        <div className="flex items-end gap-0 px-3 pt-2 border-b border-gray-800 bg-gray-950 shrink-0 overflow-x-auto">
          {tabs.map((tab) => (
            <div
              key={tab.id}
              className={`group flex items-center gap-1.5 px-3 py-2 text-xs cursor-pointer border-b-2 shrink-0 max-w-40 ${
                tab.id === activeTabId
                  ? "border-blue-500 text-gray-100"
                  : "border-transparent text-gray-500 hover:text-gray-300"
              }`}
              onClick={() => switchTab(tab.id)}
            >
              <span className="truncate">{tab.label}</span>
              <button
                className="opacity-0 group-hover:opacity-100 text-gray-600 hover:text-gray-300 transition-opacity shrink-0"
                onClick={(e) => { e.stopPropagation(); closeTab(tab.id); }}
              >
                <X size={12} />
              </button>
            </div>
          ))}
          <button
            className="px-3 py-2 text-xs text-gray-600 hover:text-gray-300 shrink-0"
            onClick={addTab}
          >
            +
          </button>
          {closedTabs.length > 0 && (
            <button
              className="px-3 py-2 text-xs text-gray-600 hover:text-gray-300 shrink-0"
              onClick={() => setHistoryOpen(true)}
              title="Recently closed"
            >
              ↺
            </button>
          )}
        </div>

        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
          {messages.map((m, i) => (
            <div key={i} className={`flex flex-col ${m.role === "user" ? "items-end" : "items-start"}`}>
              {m.role === "assistant" && m.steps && m.steps.length > 0 && (
                <div className="max-w-[75%] w-full mb-1">
                  <button
                    onClick={() => toggleSteps(i)}
                    className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-400 mb-1"
                  >
                    {expandedSteps.has(i) ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                    <span>Thought for {m.steps.length} step{m.steps.length !== 1 ? "s" : ""}</span>
                  </button>
                  {expandedSteps.has(i) && (
                    <div className="bg-gray-900 border border-gray-800 rounded-lg px-3 py-2 space-y-1.5 mb-1">
                      {m.steps.map((step, j) => (
                        <div key={j} className="flex items-start gap-2 text-xs text-gray-400">
                          <Check size={12} className="text-green-500 mt-0.5 shrink-0" />
                          {step.startsWith("Tool call: ")
                            ? <span className="font-mono text-blue-300">{step}</span>
                            : <span className="italic">{step}</span>
                          }
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
              <div className={`max-w-[75%] rounded-lg px-4 py-2 text-sm ${
                m.role === "user" ? "bg-blue-600 text-white" : "bg-gray-800 text-gray-100"
              }`}>
                {m.role === "user" ? (() => {
                  if (m.content.startsWith("[File: ")) {
                    const filename = m.content.slice(7, m.content.indexOf("]"));
                    const rest = m.content.indexOf("\n\n") >= 0 ? m.content.slice(m.content.indexOf("\n\n") + 2) : "";
                    return (
                      <div className="flex flex-col gap-1.5">
                        <span className="inline-flex items-center gap-1.5 bg-blue-500/50 rounded px-2 py-1 text-xs font-mono">
                          <Paperclip size={11} /> {filename}
                        </span>
                        {rest && <span className="whitespace-pre-wrap">{rest}</span>}
                      </div>
                    );
                  }
                  return <span className="whitespace-pre-wrap">{m.content}</span>;
                })() : renderMarkdown(m.content)}
              </div>
              {m.artifacts && m.artifacts.map((artifact, ai) => (
                <div key={ai} className="max-w-[90%] mt-2 rounded-lg border border-gray-700">
                  {artifact.artifact_type === "chart" && (
                    <div className="p-3">
                      {artifact.title && <p className="text-xs text-gray-400 mb-3">{artifact.title}</p>}
                      <ChartWidget artifact={artifact} />
                    </div>
                  )}
                  {artifact.artifact_type === "pdf" && (() => {
                    const po = artifact.data;
                    return (
                      <div className="text-xs text-gray-300">
                        {po && (
                          <>
                            <div className="flex justify-between items-start px-4 pt-4 pb-2">
                              <div>
                                <p className="font-mono text-[10px] text-gray-500 uppercase tracking-widest mb-1">Purchase Order</p>
                                <p className="text-gray-500 text-[10px]">{po.date}</p>
                              </div>
                              <p className="font-mono font-semibold text-gray-100 text-sm">{po.po_number}</p>
                            </div>
                            {po.vendor?.name && (
                              <div className="px-4 pb-2">
                                <p className="font-mono text-[10px] text-gray-500 uppercase tracking-widest mb-0.5">Vendor</p>
                                <p className="text-gray-200">{po.vendor.name}</p>
                              </div>
                            )}
                            {po.lines && po.lines.length > 0 && (
                              <div className="mx-4 mb-2 border border-gray-700 rounded overflow-hidden">
                                <table className="w-full text-[11px]">
                                  <thead>
                                    <tr className="bg-gray-800 text-gray-400 font-mono text-[9px] uppercase tracking-wider">
                                      <th className="px-3 py-2 text-left">Product</th>
                                      <th className="px-3 py-2 text-right">Qty</th>
                                      <th className="px-3 py-2 text-right">Unit Price</th>
                                      <th className="px-3 py-2 text-right">Total</th>
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {po.lines.map((line, li) => (
                                      <tr key={li} className="border-t border-gray-700">
                                        <td className="px-3 py-2">{line.product}</td>
                                        <td className="px-3 py-2 text-right text-gray-400">{line.qty}</td>
                                        <td className="px-3 py-2 text-right text-gray-400">{Number(line.unit_price).toFixed(2)}</td>
                                        <td className="px-3 py-2 text-right">{Number(line.total).toFixed(2)}</td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                            )}
                            <div className="px-4 pb-3 flex flex-col items-end gap-0.5">
                              {po.subtotal !== undefined && po.subtotal !== po.total && <p className="text-gray-500 text-[10px]">Subtotal <span className="text-gray-300 font-mono ml-2">{Number(po.subtotal).toFixed(2)}</span></p>}
                              {po.tax !== undefined && <p className="text-gray-500 text-[10px]">Tax <span className="text-gray-300 font-mono ml-2">{Number(po.tax).toFixed(2)}</span></p>}
                              {po.total !== undefined && <p className="text-gray-400 text-[11px] font-semibold">Total <span className="text-gray-100 font-mono ml-2">{Number(po.total).toFixed(2)}</span></p>}
                            </div>
                            <div className="border-t border-gray-700" />
                          </>
                        )}
                        <div className="px-3 py-2.5 flex items-center justify-between">
                          <span className="font-mono text-gray-500 text-[10px]">{artifact.title || "document"}.pdf</span>
                          <button
                            onClick={() => {
                              const a = document.createElement("a");
                              a.href = `data:application/pdf;base64,${artifact.content}`;
                              a.download = `${artifact.title || "document"}.pdf`;
                              a.click();
                            }}
                            className="text-[11px] text-gray-400 hover:text-gray-200 transition-colors"
                          >
                            Download PDF
                          </button>
                        </div>
                      </div>
                    );
                  })()}
                  {artifact.artifact_type === "image" && (
                    <>
                      {artifact.columns && (
                        <div className="flex justify-end gap-3 px-3 py-1.5 border-b border-gray-700">
                          <button onClick={() => downloadExport("csv", artifact)} className="text-xs text-gray-400 hover:text-gray-200 transition-colors">Download CSV</button>
                          <button onClick={() => downloadExport("xlsx", artifact)} className="text-xs text-gray-400 hover:text-gray-200 transition-colors">Download XLSX</button>
                          <button onClick={() => downloadExport("pdf", artifact)} className="text-xs text-gray-400 hover:text-gray-200 transition-colors">Download PDF</button>
                        </div>
                      )}
                      <div className="p-3">
                        <img src={`data:image/png;base64,${artifact.content}`} alt="table" className="max-w-full rounded" />
                      </div>
                    </>
                  )}
                  {/* artifact.artifact_type === "table" && (
                    <>
                    <div className="flex justify-end gap-3 px-3 py-1.5 border-b border-gray-700">
                      <button onClick={() => downloadExport("csv", artifact)} className="text-xs text-gray-400 hover:text-gray-200 transition-colors">Download CSV</button>
                      <button onClick={() => downloadExport("pdf", artifact)} className="text-xs text-gray-400 hover:text-gray-200 transition-colors">Download PDF</button>
                    </div>
                    <div className="overflow-x-auto">
                    <table className="w-full text-xs text-left text-gray-300">
                      <thead className="bg-gray-800 text-gray-400 uppercase">
                        <tr>
                          {artifact.columns.map((col) => (
                            <th key={col} className="px-3 py-2 font-medium whitespace-nowrap">{col}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {artifact.rows.map((row, ri) => (
                          <tr key={ri} className="border-t border-gray-700 hover:bg-gray-800/50">
                            {row.map((cell, ci) => (
                              <td key={ci} className="px-3 py-2 whitespace-nowrap">
                                {cell === null || cell === undefined ? "—" : String(cell)}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    </div>
                    </>
                  ) */}
                </div>
              ))}
            </div>
          ))}
          {loading && (
            <div className="flex flex-col items-start">
              <div className="max-w-[75%] bg-gray-900 border border-gray-800 rounded-lg px-3 py-2 space-y-1.5">
                {pendingSteps.length === 0 ? (
                  <div className="flex items-center gap-2 text-xs text-gray-500">
                    <Loader2 size={12} className="animate-spin" />
                    <span>Thinking...</span>
                  </div>
                ) : (
                  pendingSteps.map((step, i) => (
                    <div key={i} className="flex items-start gap-2 text-xs text-gray-400">
                      {i === pendingSteps.length - 1 ? (
                        <Loader2 size={12} className="text-blue-400 animate-spin mt-0.5 shrink-0" />
                      ) : (
                        <Check size={12} className="text-green-500 mt-0.5 shrink-0" />
                      )}
                      <span className="italic">{step}</span>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
          {liveTranscript && (
            <div className="flex flex-col items-end">
              <div className="max-w-[75%] rounded-lg px-4 py-2 text-sm bg-blue-600 text-white opacity-70 italic">
                {liveTranscript}
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        <div className="px-4 py-3 border-t border-gray-800 flex flex-col gap-2">
          {attachedFile && (
            <div className="flex items-center gap-2">
              <span className="text-xs bg-gray-800 text-gray-300 px-2 py-1 rounded-lg flex items-center gap-1.5 max-w-xs truncate">
                <span className="truncate">{attachedFile.name}</span>
                <button onClick={() => setAttachedFile(null)} className="text-gray-500 hover:text-gray-300 shrink-0"><X size={12} /></button>
              </span>
            </div>
          )}
          <div className="flex gap-2">
            <input
              ref={fileInputRef}
              type="file"
              className="hidden"
              accept="image/*,.pdf,.docx,.xlsx,.csv,.mp3,.wav,.m4a,.ogg"
              onChange={(e) => setAttachedFile(e.target.files?.[0] ?? null)}
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={loading}
              className="px-3 py-2 text-gray-500 hover:text-gray-300 transition-colors disabled:opacity-40"
              title="Attach file"
            >
              <Paperclip size={18} />
            </button>
            <button
              onClick={toggleRecording}
              disabled={loading}
              className={`px-3 py-2 transition-colors disabled:opacity-40 ${recording ? "text-red-500" : "text-gray-500 hover:text-gray-300"}`}
              title={recording ? "Stop recording" : "Record audio"}
            >
              {recording ? <Square size={18} /> : <Mic size={18} />}
            </button>
            <input
              className="flex-1 bg-gray-800 rounded-lg px-4 py-2 text-sm outline-none placeholder-gray-500 focus:ring-1 focus:ring-blue-600"
              placeholder="Type a message..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
              disabled={loading}
            />
            <button
              className="px-3 py-2 bg-blue-600 rounded-lg disabled:opacity-40 hover:bg-blue-500 transition-colors"
              onClick={send}
              disabled={loading || (!input.trim() && !attachedFile)}
              title="Send"
            >
              <Send size={18} />
            </button>
          </div>
        </div>
      </div>

      <div className="flex flex-col w-80 shrink-0">
        <div className="px-4 py-3 border-b border-gray-800 text-sm font-medium text-gray-400">Agent Activity</div>
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3 font-mono">
          {pendingActions.length > 0 && (
            <div className="space-y-2">
              {pendingActions.map((action) => (
                <div key={action.action_id} className="border border-yellow-800/50 rounded-lg overflow-hidden bg-gray-900">
                  <div className="px-3 pt-2.5 pb-2 border-b border-yellow-900/40">
                    <p className="text-[10px] font-mono text-yellow-600 uppercase tracking-widest">{action.agent_name || "Awaiting Confirmation"}</p>
                  </div>
                  {action.details && Object.keys(action.details).length > 0 ? (
                    <div className="px-3 py-2 space-y-1.5">
                      {Object.entries(action.details).map(([k, v]) => (
                        <div key={k} className="flex justify-between items-center">
                          <span className="text-[10px] text-gray-500 font-mono capitalize">{k.replace(/_/g, " ")}</span>
                          <span className="text-[11px] text-gray-200 font-mono">{String(v)}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="px-3 py-2">
                      <p className="text-xs text-gray-400 leading-relaxed">{action.summary}</p>
                    </div>
                  )}
                  <div className="flex border-t border-yellow-900/40">
                    <button
                      className="flex-1 px-2 py-1.5 text-xs text-gray-500 hover:text-gray-300 hover:bg-gray-800 transition-colors border-r border-yellow-900/40"
                      onClick={() => cancel(action)}
                      disabled={loading}
                    >
                      Cancel
                    </button>
                    <button
                      className="flex-1 px-2 py-1.5 text-xs text-green-400 hover:bg-green-900/30 transition-colors"
                      onClick={() => confirm(action)}
                      disabled={loading}
                    >
                      Confirm
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
          {logs.length === 0 && pendingActions.length === 0 && (
            <p className="text-xs text-gray-600">No activity yet.</p>
          )}
          {logs.map((log, i) => (
            <div key={i} className="text-xs text-gray-400">
              <span className="text-gray-600 mr-2">{log.timestamp}</span>
              {log.content}
            </div>
          ))}
          <div ref={logEndRef} />
        </div>
      </div>
      </div>

      {historyOpen && (
        <div
          className="fixed inset-0 bg-black/60 flex items-center justify-center z-50"
          onClick={() => setHistoryOpen(false)}
        >
          <div
            className="bg-gray-900 border border-gray-700 rounded-xl shadow-2xl w-96 max-h-[60vh] flex flex-col"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800">
              <span className="text-sm font-medium text-gray-300">Recently Closed</span>
              <button className="text-gray-500 hover:text-gray-300" onClick={() => setHistoryOpen(false)}><X size={16} /></button>
            </div>
            <div className="overflow-y-auto py-1">
              {closedTabs.map(tab => (
                <div key={tab.id} className="flex items-center gap-2 px-4 py-2.5 hover:bg-gray-800 group">
                  <button
                    className="flex-1 text-left text-sm text-gray-300 truncate"
                    onClick={() => restoreTab(tab)}
                  >
                    {tab.label}
                  </button>
                  <button
                    className="text-gray-600 hover:text-red-400 opacity-0 group-hover:opacity-100 shrink-0 transition-colors"
                    onClick={() => deleteClosedTab(tab.id)}
                  >
                    <X size={14} />
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
