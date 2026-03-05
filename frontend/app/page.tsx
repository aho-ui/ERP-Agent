"use client";

import { useState, useRef, useEffect } from "react";

type TableArtifact = { artifact_type: "table"; columns: string[]; rows: unknown[][] };
type ChartArtifact = { artifact_type: "chart"; image: string; title: string };
type Artifact = TableArtifact | ChartArtifact;
type Message = { role: "user" | "assistant"; content: string; steps?: string[]; artifacts?: Artifact[] };
type LogEntry = { content: string; timestamp: string };
type McpServer = { name: string; transport: string; status: "ok" | "error" };
type PendingAction = { action_id: string; summary: string; agent_name: string; timestamp: string };

const BACKEND = "http://localhost:8000";

function downloadCSV(columns: string[], rows: unknown[][], filename = "export.csv") {
  const escape = (val: unknown) => {
    const s = val === null || val === undefined ? "" : String(val);
    return s.includes(",") || s.includes('"') || s.includes("\n")
      ? `"${s.replace(/"/g, '""')}"`
      : s;
  };
  const csv = [columns.join(","), ...rows.map(r => r.map(escape).join(","))].join("\n");
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export default function Page() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [pendingSteps, setPendingSteps] = useState<string[]>([]);
  const [expandedSteps, setExpandedSteps] = useState<Set<number>>(new Set());
  const [mcpServers, setMcpServers] = useState<McpServer[]>([]);
  const [refreshInterval, setRefreshInterval] = useState(10);
  const [pendingActions, setPendingActions] = useState<PendingAction[]>([]);

  const chatEndRef = useRef<HTMLDivElement>(null);
  const logEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, pendingSteps]);
  useEffect(() => { logEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [logs]);

  useEffect(() => {
    async function fetchHealth() {
      try {
        const res = await fetch(`${BACKEND}/api/agent/mcp/health/`);
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
        const res = await fetch(`${BACKEND}/api/agent/pending/`);
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

  async function readStream(res: Response) {
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
          setMessages((prev) => [...prev, { role: "assistant", content: event.content, steps: localSteps, artifacts: localArtifacts }]);
          setPendingSteps([]);
        }
      }
    }
  }

  async function send() {
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput("");
    setLoading(true);
    setLogs([]);
    setPendingSteps([]);
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);

    const res = await fetch(`${BACKEND}/api/agent/chat/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: userMessage }),
    });

    await readStream(res);
    setLoading(false);
  }

  async function confirm(action: PendingAction) {
    setPendingActions((prev) => prev.filter((a) => a.action_id !== action.action_id));
    setLoading(true);
    setLogs([]);
    setPendingSteps([]);

    const res = await fetch(`${BACKEND}/api/agent/confirm/${action.action_id}/`, {
      method: "POST",
    });

    await readStream(res);
    setLoading(false);
  }

  async function cancel(action: PendingAction) {
    setPendingActions((prev) => prev.filter((a) => a.action_id !== action.action_id));
    await fetch(`${BACKEND}/api/agent/cancel/${action.action_id}/`, { method: "POST" });
    setMessages((prev) => [...prev, { role: "assistant", content: "Action cancelled." }]);
  }

  return (
    <div className="flex flex-col h-screen bg-gray-950 text-gray-100">
      <div className="flex items-center gap-3 px-4 py-2 border-b border-gray-800 text-xs shrink-0">
        <span className="text-gray-500 font-medium">MCP Servers</span>
        {mcpServers.map((s) => (
          <span key={s.name} className="flex items-center gap-1.5 bg-gray-800 px-2.5 py-1 rounded-full">
            <span className={`w-1.5 h-1.5 rounded-full ${s.status === "ok" ? "bg-green-400" : "bg-red-400"}`} />
            <span className="text-gray-300 capitalize">{s.name}</span>
          </span>
        ))}
        <div className="ml-auto flex items-center gap-2 text-gray-500">
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
      <div className="flex flex-col flex-1 border-r border-gray-800">
        <div className="px-4 py-3 border-b border-gray-800 text-sm font-medium text-gray-400">Chat</div>

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
              <div className={`max-w-[75%] rounded-lg px-4 py-2 text-sm whitespace-pre-wrap ${
                m.role === "user" ? "bg-blue-600 text-white" : "bg-gray-800 text-gray-100"
              }`}>
                {m.content}
              </div>
              {m.artifacts && m.artifacts.map((artifact, ai) => (
                <div key={ai} className="max-w-[90%] mt-2 rounded-lg border border-gray-700">
                  {artifact.artifact_type === "chart" && (
                    <div className="p-3">
                      {artifact.title && <p className="text-xs text-gray-400 mb-2">{artifact.title}</p>}
                      <img src={artifact.image} alt={artifact.title} className="w-full rounded" />
                    </div>
                  )}
                  {artifact.artifact_type === "table" && (
                    <>
                    <div className="flex justify-end px-2 py-1 border-b border-gray-700">
                      <button
                        className="text-xs text-gray-400 hover:text-gray-200 transition-colors"
                        onClick={() => downloadCSV(artifact.columns, artifact.rows)}
                      >
                        Download CSV
                      </button>
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
    </div>
  );
}
