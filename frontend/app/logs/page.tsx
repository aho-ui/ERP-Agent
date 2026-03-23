"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";

const BACKEND = "http://localhost:8000";

type ArtifactItem =
  | { artifact_type: "table"; columns: string[]; rows: unknown[][]; title?: string }
  | { artifact_type: "chart"; chart_type: "bar" | "line" | "pie"; title: string; x_key?: string; series?: { key: string; label: string }[]; data: Record<string, unknown>[] }
  | { artifact_type: string; [key: string]: unknown };

type LogRow = {
  id: string;
  intent: string;
  agent_name: string;
  tool_called: string;
  status: "success" | "failed" | "pending";
  timestamp: string;
  output: Record<string, unknown>;
  artifacts: ArtifactItem[];
};

const STATUS_STYLES: Record<string, string> = {
  success: "text-green-400",
  failed: "text-red-400",
  pending: "text-yellow-400",
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

export default function LogsPage() {
  const router = useRouter();
  const [logs, setLogs] = useState<LogRow[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) { router.replace("/login"); return; }
    if (localStorage.getItem("user_role") !== "admin") { router.replace("/"); return; }
    fetch(`${BACKEND}/api/agent/logs/`, { headers: { "Authorization": `Bearer ${token}` } })
      .then((r) => r.json())
      .then(setLogs)
      .catch(() => {});
  }, [router]);

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <div className="flex items-center gap-4 px-6 py-3 border-b border-gray-800 text-sm">
        <Link href="/" className="text-gray-400 hover:text-gray-200 transition-colors">
          Chat
        </Link>
        <span className="text-gray-600">/</span>
        <span className="text-gray-200">Audit Logs</span>
      </div>

      <div className="px-6 py-6">
        <div className="rounded-lg border border-gray-800 overflow-hidden">
          <table className="w-full text-sm text-left">
            <thead className="bg-gray-800 text-gray-400 text-xs uppercase">
              <tr>
                <th className="px-4 py-3 font-medium">Timestamp</th>
                <th className="px-4 py-3 font-medium">Agent</th>
                <th className="px-4 py-3 font-medium">Intent</th>
                <th className="px-4 py-3 font-medium">Tools Used</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Output</th>
              </tr>
            </thead>
            <tbody>
              {logs.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-6 text-center text-gray-600 text-xs">
                    No logs found.
                  </td>
                </tr>
              )}
              {logs.map((log) => (
                <React.Fragment key={log.id}>
                  <tr
                    className="border-t border-gray-800 hover:bg-gray-900/50 cursor-pointer"
                    onClick={() => setExpanded(expanded === log.id ? null : log.id)}
                  >
                    <td className="px-4 py-3 text-xs text-gray-400 whitespace-nowrap font-mono">
                      {new Date(log.timestamp).toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-300 whitespace-nowrap">{log.agent_name || "—"}</td>
                    <td className="px-4 py-3 text-xs text-gray-200 max-w-xs truncate">{log.intent}</td>
                    <td className="px-4 py-3 text-xs text-gray-400 font-mono max-w-xs truncate">{log.tool_called || "—"}</td>
                    <td className={`px-4 py-3 text-xs font-medium ${STATUS_STYLES[log.status] ?? "text-gray-400"}`}>
                      {log.status}
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-500">
                      <span className="font-mono">{expanded === log.id ? "▾" : "▸"}</span>
                    </td>
                  </tr>
                  {expanded === log.id && (
                    <tr key={`${log.id}-expanded`} className="border-t border-gray-800 bg-gray-900/30">
                      <td colSpan={6} className="px-4 py-4 space-y-4">
                        {log.output?.tokens && (
                          <div className="flex gap-4 text-xs font-mono text-gray-500">
                            <span>prompt <span className="text-gray-300">{(log.output.tokens as {prompt:number}).prompt}</span></span>
                            <span>completion <span className="text-gray-300">{(log.output.tokens as {completion:number}).completion}</span></span>
                            <span>total <span className="text-gray-300">{(log.output.tokens as {total:number}).total}</span></span>
                          </div>
                        )}
                        <pre className="text-xs text-gray-400 whitespace-pre-wrap font-mono">
                          {JSON.stringify(log.output, null, 2)}
                        </pre>
                        {log.artifacts && log.artifacts.length > 0 && (
                          <div className="space-y-3">
                            {log.artifacts.map((artifact, ai) => (
                              <div key={ai} className="rounded border border-gray-700">
                                {artifact.artifact_type === "chart" && (() => {
                                  const a = artifact as Extract<ArtifactItem, { artifact_type: "chart" }>;
                                  return (
                                    <div className="p-3">
                                      {a.title && <p className="text-xs text-gray-400 mb-2">{a.title}</p>}
                                      <LogChartWidget artifact={a} />
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
                                          <tr>{t.columns.map((col) => <th key={col} className="px-3 py-2 font-medium whitespace-nowrap">{col}</th>)}</tr>
                                        </thead>
                                        <tbody>
                                          {t.rows.map((row, ri) => (
                                            <tr key={ri} className="border-t border-gray-700">
                                              {(row as unknown[]).map((cell, ci) => (
                                                <td key={ci} className="px-3 py-2 whitespace-nowrap">{cell === null || cell === undefined ? "—" : String(cell)}</td>
                                              ))}
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
              ))}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
}
