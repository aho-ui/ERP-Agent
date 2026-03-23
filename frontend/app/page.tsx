"use client";

import { useState, useRef, useEffect, useMemo } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";

type TableArtifact = { artifact_type: "table"; columns: string[]; rows: unknown[][]; title?: string };
type ChartArtifact = { artifact_type: "chart"; chart_type: "bar" | "line" | "pie"; title: string; x_key?: string; series?: { key: string; label: string }[]; data: Record<string, unknown>[] };
type Artifact = TableArtifact | ChartArtifact;
type Message = { role: "user" | "assistant"; content: string; steps?: string[]; artifacts?: Artifact[] };
type Tab = { id: string; label: string; messages: Message[] };
type LogEntry = { content: string; timestamp: string };
type McpServer = { name: string; transport: string; status: "ok" | "error" };
type PendingAction = { action_id: string; summary: string; agent_name: string; timestamp: string };

const BACKEND = "http://localhost:8000";

function newTab(n: number): Tab {
  return { id: crypto.randomUUID(), label: `Chat ${n}`, messages: [] };
}

function loadTabs(username: string): Tab[] {
  try {
    const saved = JSON.parse(localStorage.getItem(`chat_tabs_${username}`) ?? "[]") as Tab[];
    if (saved.length > 0) return saved;
  } catch {}
  return [newTab(1)];
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
      <ResponsiveContainer width="100%" height={260}>
        <PieChart>
          <Pie data={data} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={90} label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
            {data.map((_, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
          </Pie>
          <Tooltip />
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

const _blank = newTab(1);

export default function Page() {
  const router = useRouter();
  const [username, setUsername] = useState<string>("");
  const [tabs, setTabs] = useState<Tab[]>([_blank]);
  const [activeTabId, setActiveTabId] = useState<string>(_blank.id);
  const [closedTabs, setClosedTabs] = useState<Tab[]>([]);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [pendingSteps, setPendingSteps] = useState<string[]>([]);
  const [expandedSteps, setExpandedSteps] = useState<Set<number>>(new Set());
  const [mcpServers, setMcpServers] = useState<McpServer[]>([]);
  const [refreshInterval, setRefreshInterval] = useState(10);
  const [pendingActions, setPendingActions] = useState<PendingAction[]>([]);
  const [userRole, setUserRole] = useState<string>("");

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) { router.replace("/login"); return; }
    setUserRole(localStorage.getItem("user_role") ?? "");
    const u = localStorage.getItem("username") ?? "";
    setUsername(u);
    if (u) {
      const savedTabs = loadTabs(u);
      setTabs(savedTabs);
      setActiveTabId(savedTabs[0].id);
      try {
        const closed = JSON.parse(localStorage.getItem(`chat_closed_tabs_${u}`) ?? "[]") as Tab[];
        setClosedTabs(closed);
      } catch {}
    }
  }, [router]);

  function authHeader() {
    const token = localStorage.getItem("access_token") ?? "";
    return { "Authorization": `Bearer ${token}` };
  }

  async function downloadExport(type: "csv" | "pdf", artifact: TableArtifact) {
    const res = await fetch(`${BACKEND}/api/agent/export/${type}/`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeader() },
      body: JSON.stringify({ columns: artifact.columns, rows: artifact.rows, title: artifact.title ?? "" }),
    });
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${artifact.title || "export"}.${type}`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function logout() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("user_role");
    localStorage.removeItem("username");
    router.replace("/login");
  }

  const activeTab = tabs.find(t => t.id === activeTabId) ?? tabs[0];
  const messages = useMemo(() => activeTab?.messages ?? [], [activeTab]);

  function updateMessages(tabId: string, updater: (prev: Message[]) => Message[]) {
    setTabs(prev => prev.map(t => t.id === tabId ? { ...t, messages: updater(t.messages) } : t));
  }

  function addTab() {
    const t = newTab(tabs.length + 1);
    setTabs(prev => [...prev, t]);
    setActiveTabId(t.id);
    setExpandedSteps(new Set());
  }

  function closeTab(id: string) {
    const closing = tabs.find(t => t.id === id);
    if (closing) {
      setClosedTabs(c => [closing, ...c].slice(0, 10));
    }
    setTabs(prev => {
      const next = prev.filter(t => t.id !== id);
      if (next.length === 0) {
        const t = newTab(1);
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
    setClosedTabs(prev => prev.filter(t => t.id !== tab.id));
    setTabs(prev => [...prev, tab]);
    setActiveTabId(tab.id);
    setExpandedSteps(new Set());
    setHistoryOpen(false);
  }

  function deleteClosedTab(id: string) {
    setClosedTabs(prev => prev.filter(t => t.id !== id));
  }

  function switchTab(id: string) {
    setActiveTabId(id);
    setExpandedSteps(new Set());
  }

  useEffect(() => {
    if (!username) return;
    try { localStorage.setItem(`chat_tabs_${username}`, JSON.stringify(tabs)); } catch {}
  }, [tabs, username]);

  useEffect(() => {
    if (!username) return;
    try { localStorage.setItem(`chat_closed_tabs_${username}`, JSON.stringify(closedTabs)); } catch {}
  }, [closedTabs, username]);

  const chatEndRef = useRef<HTMLDivElement>(null);
  const logEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, pendingSteps]);
  useEffect(() => { logEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [logs]);

  useEffect(() => {
    async function fetchHealth() {
      try {
        const res = await fetch(`${BACKEND}/api/agent/mcp/health/`, { headers: authHeader() });
        const data = await res.json();
        setMcpServers(data);
      } catch {}
    }
    fetchHealth();
    const id = setInterval(fetchHealth, refreshInterval * 1000);
    return () => clearInterval(id);
  }, [refreshInterval]);

  useEffect(() => {
    async function fetchPending() {
      try {
        const res = await fetch(`${BACKEND}/api/agent/pending/`, { headers: authHeader() });
        const data: PendingAction[] = await res.json();
        setPendingActions(data);
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
        } else if (event.type === "confirmation") {
          setPendingActions((prev) => [
            ...prev,
            {
              action_id: event.action_id,
              summary: event.summary,
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

  async function send() {
    if (!input.trim() || loading) return;

    const tabId = activeTabId;
    const userMessage = input.trim();
    setInput("");
    setLoading(true);
    setLogs([]);
    setPendingSteps([]);

    const isFirst = (tabs.find(t => t.id === tabId)?.messages ?? []).length === 0;
    if (isFirst) {
      setTabs(prev => prev.map(t => t.id === tabId ? { ...t, label: userMessage.slice(0, 22) } : t));
    }

    updateMessages(tabId, prev => [...prev, { role: "user", content: userMessage }]);

    const res = await fetch(`${BACKEND}/api/agent/chat/`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeader() },
      body: JSON.stringify({ message: userMessage, session_key: tabId }),
    });

    await readStream(res, tabId);
    setLoading(false);
  }

  async function confirm(action: PendingAction) {
    const tabId = activeTabId;
    setPendingActions((prev) => prev.filter((a) => a.action_id !== action.action_id));
    setLoading(true);
    setLogs([]);
    setPendingSteps([]);

    const res = await fetch(`${BACKEND}/api/agent/confirm/${action.action_id}/`, {
      method: "POST",
      headers: authHeader(),
    });

    await readStream(res, tabId);
    setLoading(false);
  }

  async function cancel(action: PendingAction) {
    const tabId = activeTabId;
    setPendingActions((prev) => prev.filter((a) => a.action_id !== action.action_id));
    await fetch(`${BACKEND}/api/agent/cancel/${action.action_id}/`, { method: "POST", headers: authHeader() });
    updateMessages(tabId, prev => [...prev, { role: "assistant", content: "Action cancelled." }]);
  }

  return (
    <div className="flex flex-col h-screen bg-gray-950 text-gray-100">
      <div className="flex items-center gap-3 px-4 py-2 border-b border-gray-800 text-xs shrink-0">
        <Link href="/agents" className="text-gray-400 hover:text-gray-200 transition-colors font-medium">Agents</Link>
        {userRole === "admin" && (
          <>
            <span className="text-gray-700">|</span>
            <Link href="/logs" className="text-gray-400 hover:text-gray-200 transition-colors font-medium">Logs</Link>
            <span className="text-gray-700">|</span>
            <Link href="/users" className="text-gray-400 hover:text-gray-200 transition-colors font-medium">Users</Link>
          </>
        )}
        <span className="text-gray-700">|</span>
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
        <button
          className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
          onClick={logout}
        >
          Sign out
        </button>
        <span className="text-gray-700">|</span>
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
                className="opacity-0 group-hover:opacity-100 text-gray-600 hover:text-gray-300 transition-opacity leading-none shrink-0"
                onClick={(e) => { e.stopPropagation(); closeTab(tab.id); }}
              >
                ×
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
                    <span className="font-mono">{expandedSteps.has(i) ? "▾" : "▸"}</span>
                    <span>Thought for {m.steps.length} step{m.steps.length !== 1 ? "s" : ""}</span>
                  </button>
                  {expandedSteps.has(i) && (
                    <div className="bg-gray-900 border border-gray-800 rounded-lg px-3 py-2 space-y-1.5 mb-1">
                      {m.steps.map((step, j) => (
                        <div key={j} className="flex items-start gap-2 text-xs text-gray-400">
                          <span className="text-green-500 mt-0.5 shrink-0">✓</span>
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
                m.role === "user" ? "bg-blue-600 text-white whitespace-pre-wrap" : "bg-gray-800 text-gray-100"
              }`}>
                {m.role === "user" ? m.content : renderMarkdown(m.content)}
              </div>
              {m.artifacts && m.artifacts.map((artifact, ai) => (
                <div key={ai} className="max-w-[90%] mt-2 rounded-lg border border-gray-700">
                  {artifact.artifact_type === "chart" && (
                    <div className="p-3">
                      {artifact.title && <p className="text-xs text-gray-400 mb-3">{artifact.title}</p>}
                      <ChartWidget artifact={artifact} />
                    </div>
                  )}
                  {artifact.artifact_type === "table" && (
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
                  )}
                </div>
              ))}
            </div>
          ))}
          {loading && (
            <div className="flex flex-col items-start">
              <div className="max-w-[75%] bg-gray-900 border border-gray-800 rounded-lg px-3 py-2 space-y-1.5">
                {pendingSteps.length === 0 ? (
                  <div className="flex items-center gap-2 text-xs text-gray-500">
                    <span className="animate-pulse">●</span>
                    <span>Thinking...</span>
                  </div>
                ) : (
                  pendingSteps.map((step, i) => (
                    <div key={i} className="flex items-start gap-2 text-xs text-gray-400">
                      {i === pendingSteps.length - 1 ? (
                        <span className="text-blue-400 animate-pulse mt-0.5 shrink-0">●</span>
                      ) : (
                        <span className="text-green-500 mt-0.5 shrink-0">✓</span>
                      )}
                      <span className="italic">{step}</span>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        <div className="px-4 py-3 border-t border-gray-800 flex gap-2">
          <input
            className="flex-1 bg-gray-800 rounded-lg px-4 py-2 text-sm outline-none placeholder-gray-500 focus:ring-1 focus:ring-blue-600"
            placeholder="Type a message..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
            disabled={loading}
          />
          <button
            className="px-4 py-2 bg-blue-600 rounded-lg text-sm font-medium disabled:opacity-40 hover:bg-blue-500 transition-colors"
            onClick={send}
            disabled={loading}
          >
            Send
          </button>
        </div>
      </div>

      <div className="flex flex-col w-80 shrink-0">
        <div className="px-4 py-3 border-b border-gray-800 text-sm font-medium text-gray-400">Agent Activity</div>
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3 font-mono">
          {pendingActions.length > 0 && (
            <div className="space-y-2">
              {pendingActions.map((action) => (
                <div key={action.action_id} className="bg-yellow-950/40 border border-yellow-800/50 rounded-lg px-3 py-2 space-y-2">
                  <p className="text-xs text-yellow-400 leading-relaxed">{action.summary}</p>
                  <div className="flex gap-2">
                    <button
                      className="flex-1 px-2 py-1 text-xs bg-gray-700 rounded hover:bg-gray-600 transition-colors"
                      onClick={() => cancel(action)}
                      disabled={loading}
                    >
                      Cancel
                    </button>
                    <button
                      className="flex-1 px-2 py-1 text-xs bg-green-700 rounded hover:bg-green-600 transition-colors"
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
              <button className="text-gray-500 hover:text-gray-300 text-lg leading-none" onClick={() => setHistoryOpen(false)}>×</button>
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
                    className="text-gray-600 hover:text-red-400 text-sm opacity-0 group-hover:opacity-100 shrink-0 transition-colors"
                    onClick={() => deleteClosedTab(tab.id)}
                  >
                    ×
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
