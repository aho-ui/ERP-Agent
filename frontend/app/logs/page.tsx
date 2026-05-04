"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useApi, BACKEND } from "../lib/api";
import { BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";

// const BACKEND = "http://localhost:8000";

type ArtifactItem =
  | { artifact_type: "table"; columns: string[]; rows: string[][]; title?: string }
  | { artifact_type: "chart"; chart_type: "bar" | "line" | "pie"; title: string; x_key?: string; series?: { key: string; label: string }[]; data: Record<string, unknown>[] }
  | { artifact_type: "pdf"; title: string; content?: string; data?: Record<string, unknown> }
  | { artifact_type: string; [key: string]: unknown };

type LogRow = {
  id: string;
  run_id: string | null;
  source: string;
  intent: string;
  agent_name: string;
  tool_called: string;
  status: "success" | "failed" | "pending" | "approved";
  timestamp: string;
  output: Record<string, unknown>;
  artifacts: ArtifactItem[];
};

type LogGroup = {
  run_id: string | null;
  rows: LogRow[];
};

const STATUS_STYLES: Record<string, string> = {
  success: "text-green-400",
  failed: "text-red-400",
  pending: "text-yellow-400",
  approved: "text-blue-400",
};

const CHART_COLORS = ["#6366f1", "#22d3ee", "#f59e0b", "#10b981", "#f43f5e", "#a78bfa"];

function LogChartWidget({ artifact }: { artifact: Extract<ArtifactItem, { artifact_type: "chart" }> }) {
  const { chart_type, data, x_key, series } = artifact;
  if (chart_type === "pie") {
    return (
      <ResponsiveContainer width="100%" height={220}>
        <PieChart>
          <Pie data={data} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
            {data.map((_, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
          </Pie>
          <Tooltip />
        </PieChart>
      </ResponsiveContainer>
    );
  }
  if (chart_type === "line") {
    return (
      <ResponsiveContainer width="100%" height={220}>
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
    <ResponsiveContainer width="100%" height={220}>
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

async function downloadExport(type: "csv" | "pdf", artifact: Extract<ArtifactItem, { artifact_type: "table" }>) {
  const token = localStorage.getItem("access_token") ?? "";
  const res = await fetch(`${BACKEND}/api/agent/export/${type}/`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
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

function SingleLogRow({ log, expanded, setExpanded, indent = false }: { log: LogRow; expanded: string | null; setExpanded: (id: string | null) => void; indent?: boolean }) {
  return (
    <React.Fragment>
      <tr
        className={`border-t border-gray-800 hover:bg-gray-900/50 cursor-pointer${indent ? " bg-gray-900/20" : ""}`}
        onClick={() => setExpanded(expanded === log.id ? null : log.id)}
      >
        <td className={`py-3 text-xs text-gray-400 whitespace-nowrap font-mono${indent ? " pl-8 pr-4" : " px-4"}`}>{new Date(log.timestamp).toLocaleString()}</td>
        <td className="px-4 py-3 text-xs text-gray-500 capitalize whitespace-nowrap">{log.source || "web"}</td>
        <td className="px-4 py-3 text-xs text-gray-300 whitespace-nowrap">{log.agent_name || "—"}</td>
        <td className="px-4 py-3 text-xs text-gray-200 max-w-xs truncate">{log.intent}</td>
        <td className="px-4 py-3 text-xs text-gray-400 font-mono max-w-xs truncate">{log.tool_called || "—"}</td>
        <td className={`px-4 py-3 text-xs font-medium ${STATUS_STYLES[log.status] ?? "text-gray-400"}`}>{log.status}</td>
        <td className="px-4 py-3 text-xs text-gray-500"><span className="font-mono">{expanded === log.id ? "▾" : "▸"}</span></td>
      </tr>
      {expanded === log.id && (
        <tr className="border-t border-gray-800 bg-gray-900/30">
          <td colSpan={7} className="px-4 py-4 space-y-4">
            {!!log.output?.tokens && (() => {
              const t = log.output.tokens as { prompt: number; completion: number; total: number };
              return (
                <div className="flex gap-4 text-xs font-mono text-gray-500">
                  <span>prompt <span className="text-gray-300">{t.prompt}</span></span>
                  <span>completion <span className="text-gray-300">{t.completion}</span></span>
                  <span>total <span className="text-gray-300">{t.total}</span></span>
                </div>
              );
            })()}
            <pre className="text-xs text-gray-400 whitespace-pre-wrap font-mono">{JSON.stringify(log.output, null, 2)}</pre>
            {log.artifacts && log.artifacts.length > 0 && (
              <div className="space-y-3">
                {log.artifacts.map((artifact, ai) => (
                  <div key={ai} className="rounded border border-gray-700">
                    {artifact.artifact_type === "chart" && (() => {
                      const a = artifact as Extract<ArtifactItem, { artifact_type: "chart" }>;
                      return <div className="p-3">{a.title && <p className="text-xs text-gray-400 mb-2">{a.title}</p>}<LogChartWidget artifact={a} /></div>;
                    })()}
                    {artifact.artifact_type === "pdf" && (() => {
                      const p = artifact as Extract<ArtifactItem, { artifact_type: "pdf" }>;
                      return (
                        <div className="flex items-center justify-between px-3 py-2">
                          <span className="text-xs text-gray-400 font-mono">{p.title}.pdf</span>
                          {p.content && (
                            <button onClick={() => { const bytes = Uint8Array.from(atob(p.content!), c => c.charCodeAt(0)); const blob = new Blob([bytes], { type: "application/pdf" }); const url = URL.createObjectURL(blob); const a = document.createElement("a"); a.href = url; a.download = `${p.title}.pdf`; a.click(); URL.revokeObjectURL(url); }} className="text-xs text-gray-400 hover:text-gray-200 transition-colors">Download PDF</button>
                          )}
                        </div>
                      );
                    })()}
                    {artifact.artifact_type === "table" && (() => {
                      const t = artifact as Extract<ArtifactItem, { artifact_type: "table" }>;
                      return (
                        <>
                          <div className="flex justify-end gap-3 px-3 py-1.5 border-b border-gray-700">
                            <button onClick={() => downloadExport("csv", t)} className="text-xs text-gray-400 hover:text-gray-200 transition-colors">Download CSV</button>
                            <button onClick={() => downloadExport("pdf", t)} className="text-xs text-gray-400 hover:text-gray-200 transition-colors">Download PDF</button>
                          </div>
                          <div className="overflow-x-auto">
                            <table className="w-full text-xs text-left text-gray-300">
                              <thead className="bg-gray-800 text-gray-400 uppercase">
                                <tr>{t.columns.map(col => <th key={col} className="px-3 py-2 font-medium whitespace-nowrap">{col}</th>)}</tr>
                              </thead>
                              <tbody>
                                {t.rows.map((row, ri) => (
                                  <tr key={ri} className="border-t border-gray-700">
                                    {(row as unknown[]).map((cell, ci) => <td key={ci} className="px-3 py-2 whitespace-nowrap">{cell === null || cell === undefined ? "—" : String(cell)}</td>)}
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </>
                      );
                    })()}
                  </div>
                ))}
              </div>
            )}
          </td>
        </tr>
      )}
    </React.Fragment>
  );
}

export default function LogsPage() {
  const router = useRouter();
  const { apiFetch, authHeader } = useApi();
  const [logs, setLogs] = useState<LogRow[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());
  const [sourceFilter, setSourceFilter] = useState<string>("all");

  useEffect(() => {
    if (!localStorage.getItem("access_token")) { router.replace("/login"); return; }
    // if (localStorage.getItem("user_role") !== "admin") { router.replace("/"); return; }
    const role = localStorage.getItem("user_role");
    if (role !== "operator" && role !== "admin") { router.replace("/"); return; }
    apiFetch<LogRow[]>(`${BACKEND}/api/agent/actions/`)
      .then(data => data && Array.isArray(data) ? setLogs(data) : {})
      .catch(() => {});
  }, [router]);

  return (
    <div className="h-full overflow-y-auto bg-gray-950 text-gray-100">
      {/* <div className="flex items-center gap-4 px-6 py-3 border-b border-gray-800 text-sm">
        Chat / Audit Logs
      </div> */}

      <div className="px-6 py-6">
        <div className="flex items-center justify-between mb-3">
          <div className="flex gap-1">
            {["all", "web", "discord", "telegram", "system"].map(s => (
              <button
                key={s}
                onClick={() => setSourceFilter(s)}
                className={`text-xs px-2.5 py-1 rounded transition-colors capitalize ${sourceFilter === s ? "bg-blue-600 text-white" : "text-gray-500 hover:text-gray-300 border border-gray-800"}`}
              >
                {s}
              </button>
            ))}
          </div>
          <button
            onClick={() => {
              fetch(`${BACKEND}/api/agent/actions/?format=csv`, { headers: authHeader() })
                .then(r => r.blob())
                .then(blob => {
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement("a");
                  a.href = url; a.download = "audit_log.csv"; a.click();
                  URL.revokeObjectURL(url);
                });
            }}
            className="text-xs text-gray-400 hover:text-gray-200 transition-colors border border-gray-700 px-3 py-1.5 rounded"
          >
            Export CSV
          </button>
        </div>

        {logs.length === 0 && (
          <p className="text-xs text-gray-600 text-center py-8">No logs found.</p>
        )}

        {(() => {
          const filtered = sourceFilter === "all" ? logs : logs.filter(l => l.source === sourceFilter);
          const groups: LogGroup[] = [];
          const seen = new Map<string, LogGroup>();
          for (const log of filtered) {
            if (log.run_id) {
              if (!seen.has(log.run_id)) {
                const g: LogGroup = { run_id: log.run_id, rows: [] };
                seen.set(log.run_id, g);
                groups.push(g);
              }
              seen.get(log.run_id)!.rows.push(log);
            } else {
              groups.push({ run_id: null, rows: [log] });
            }
          }
          return (
            <div className="rounded-lg border border-gray-800 overflow-hidden">
              <table className="w-full text-xs text-left">
                <thead className="bg-gray-900 text-gray-500 uppercase sticky top-0">
                  <tr>
                    <th className="px-4 py-2 font-medium">Timestamp</th>
                    <th className="px-4 py-2 font-medium">Source</th>
                    <th className="px-4 py-2 font-medium">Agent</th>
                    <th className="px-4 py-2 font-medium">Intent</th>
                    <th className="px-4 py-2 font-medium">Tools Used</th>
                    <th className="px-4 py-2 font-medium">Status</th>
                    <th className="px-4 py-2 font-medium w-6"></th>
                  </tr>
                </thead>
                <tbody>
                  {groups.map((group) => {
                    if (!group.run_id) {
                      const log = group.rows[0];
                      return <SingleLogRow key={log.id} log={log} expanded={expanded} setExpanded={setExpanded} />;
                    }
                    const isOpen = expandedGroups.has(group.run_id);
                    const first = group.rows[0];
                    const agents = [...new Set(group.rows.map(r => r.agent_name).filter(Boolean))].join(", ");
                    const overallStatus = group.rows.some(r => r.status === "failed") ? "failed"
                      : group.rows.some(r => r.status === "pending") ? "pending"
                      : group.rows.some(r => r.status === "approved") ? "approved"
                      : "success";
                    return (
                      <React.Fragment key={group.run_id}>
                        <tr
                          className="border-t border-gray-800 bg-gray-900/60 hover:bg-gray-800/80 cursor-pointer"
                          onClick={() => setExpandedGroups(prev => {
                            const next = new Set(prev);
                            isOpen ? next.delete(group.run_id!) : next.add(group.run_id!);
                            return next;
                          })}
                        >
                          <td className="px-4 py-3 text-gray-400 font-mono whitespace-nowrap">{new Date(first.timestamp).toLocaleString()}</td>
                          <td className="px-4 py-3 text-gray-500 capitalize">{first.source || "web"}</td>
                          <td className="px-4 py-3 text-gray-500">{agents}</td>
                          <td className="px-4 py-3 text-gray-200 max-w-xs">
                            <span className="flex items-center gap-2">
                              <span className="text-gray-600 font-mono">{isOpen ? "▾" : "▸"}</span>
                              <span className="truncate">{first.intent}</span>
                            </span>
                          </td>
                          <td className="px-4 py-3 text-gray-600">{group.rows.length} action{group.rows.length !== 1 ? "s" : ""}</td>
                          <td className={`px-4 py-3 font-medium ${STATUS_STYLES[overallStatus] ?? "text-gray-400"}`}>{overallStatus}</td>
                          <td></td>
                        </tr>
                        {isOpen && group.rows.map(log => (
                          <SingleLogRow key={log.id} log={log} expanded={expanded} setExpanded={setExpanded} indent />
                        ))}
                      </React.Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
          );
        })()}
      </div>

    </div>
  );
}
