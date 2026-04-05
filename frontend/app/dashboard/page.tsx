"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useApi, BACKEND } from "../lib/api";
import {
  BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from "recharts";

// const BACKEND = "http://localhost:8000";

const COLORS = ["#6366f1", "#22d3ee", "#f59e0b", "#10b981", "#f43f5e", "#a78bfa"];
const STATUS_COLOR: Record<string, string> = {
  success: "#10b981",
  failed: "#f43f5e",
  pending: "#f59e0b",
  approved: "#60a5fa",
};
const STATUS_TEXT: Record<string, string> = {
  success: "text-green-400",
  failed: "text-red-400",
  pending: "text-yellow-400",
  approved: "text-blue-400",
};

type McpEntry = {
  name: string;
  healthy: boolean;
  stats: Record<string, number> | null;
};

type AgentEntry = { name: string; count: number };
type StatusEntry = { name: string; value: number };

type AgentCallGroup = {
  total: number;
  agents: AgentEntry[];
  statuses: StatusEntry[];
};

type DashboardData = {
  mcps: McpEntry[];
  agent_calls: Record<string, AgentCallGroup>;
};

type CallRecord = {
  id: string;
  agent_name: string;
  tool_called: string;
  intent: string;
  input_params: Record<string, unknown>;
  output: Record<string, unknown>;
  status: string;
  timestamp: string;
};

function KpiCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl border border-gray-800 bg-gray-900/60 px-5 py-4 flex flex-col gap-1">
      <p className="text-xs text-gray-500 capitalize">{label.replace(/_/g, " ")}</p>
      <p className="text-3xl font-semibold text-white tabular-nums">{value.toLocaleString()}</p>
    </div>
  );
}

function SectionHeading({ children }: { children: React.ReactNode }) {
  return <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-3">{children}</h3>;
}

function McpPanel({
  mcp,
  calls,
  callsLoaded,
}: {
  mcp: McpEntry;
  calls: CallRecord[];
  callsLoaded: boolean;
}) {
  const [expandedCall, setExpandedCall] = useState<string | null>(null);

  const statusData = calls.reduce<StatusEntry[]>((acc, c) => {
    const existing = acc.find((s) => s.name === c.status);
    if (existing) existing.value++;
    else acc.push({ name: c.status, value: 1 });
    return acc;
  }, []);

  return (
    <div className="space-y-8">
      {mcp.stats && Object.keys(mcp.stats).length > 0 && (
        <div>
          <SectionHeading>Overview</SectionHeading>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
            {Object.entries(mcp.stats).map(([k, v]) => (
              <KpiCard key={k} label={k} value={v} />
            ))}
          </div>
        </div>
      )}

      {!mcp.healthy && (
        <div className="rounded-xl border border-red-900/40 bg-red-950/20 px-5 py-4 text-sm text-red-400">
          MCP server is offline. Stats unavailable.
        </div>
      )}

      {callsLoaded && calls.length > 0 && (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="rounded-xl border border-gray-800 bg-gray-900/60 p-5">
              <SectionHeading>Agent Usage</SectionHeading>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart
                  data={calls.reduce<AgentEntry[]>((acc, c) => {
                    const existing = acc.find((a) => a.name === c.agent_name);
                    if (existing) existing.count++;
                    else acc.push({ name: c.agent_name || "unknown", count: 1 });
                    return acc;
                  }, []).sort((a, b) => b.count - a.count)}
                  layout="vertical"
                  margin={{ left: 8, right: 16, top: 4, bottom: 4 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" horizontal={false} />
                  <XAxis type="number" tick={{ fontSize: 10, fill: "#6b7280" }} />
                  <YAxis type="category" dataKey="name" tick={{ fontSize: 10, fill: "#9ca3af" }} width={100} />
                  <Tooltip contentStyle={{ backgroundColor: "#111827", border: "1px solid #1f2937", fontSize: 11 }} />
                  <Bar dataKey="count" fill="#6366f1" radius={[0, 3, 3, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="rounded-xl border border-gray-800 bg-gray-900/60 p-5">
              <SectionHeading>Call Status</SectionHeading>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie
                    data={statusData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={75}
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    labelLine={false}
                  >
                    {statusData.map((s, i) => (
                      <Cell key={s.name} fill={STATUS_COLOR[s.name] ?? COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ backgroundColor: "#111827", border: "1px solid #1f2937", fontSize: 11, color: "#f3f4f6" }} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="rounded-xl border border-gray-800 overflow-hidden">
            <div className="px-5 py-3 bg-gray-900/60 border-b border-gray-800">
              <SectionHeading>Recent Calls</SectionHeading>
            </div>
            <table className="w-full text-xs text-left">
              <thead className="bg-gray-900/40 text-gray-500 uppercase">
                <tr>
                  <th className="px-4 py-2 font-medium">Timestamp</th>
                  <th className="px-4 py-2 font-medium">Agent</th>
                  <th className="px-4 py-2 font-medium">Intent</th>
                  <th className="px-4 py-2 font-medium">Tools</th>
                  <th className="px-4 py-2 font-medium">Status</th>
                  <th className="px-4 py-2 font-medium w-6"></th>
                </tr>
              </thead>
              <tbody>
                {calls.map((c) => (
                  <React.Fragment key={c.id}>
                    <tr
                      className="border-t border-gray-800 hover:bg-gray-900/40 cursor-pointer"
                      onClick={() => setExpandedCall(expandedCall === c.id ? null : c.id)}
                    >
                      <td className="px-4 py-2.5 text-gray-400 font-mono whitespace-nowrap">
                        {new Date(c.timestamp).toLocaleString()}
                      </td>
                      <td className="px-4 py-2.5 text-gray-300 whitespace-nowrap">{c.agent_name || "—"}</td>
                      <td className="px-4 py-2.5 text-gray-200 max-w-xs truncate">{c.intent}</td>
                      <td className="px-4 py-2.5 text-gray-500 font-mono max-w-xs truncate">{c.tool_called || "—"}</td>
                      <td className={`px-4 py-2.5 font-medium ${STATUS_TEXT[c.status] ?? "text-gray-400"}`}>
                        {c.status}
                      </td>
                      <td className="px-4 py-2.5 text-gray-600 font-mono">
                        {expandedCall === c.id ? "▾" : "▸"}
                      </td>
                    </tr>
                    {expandedCall === c.id && (
                      <tr className="border-t border-gray-800 bg-gray-950/60">
                        <td colSpan={6} className="px-4 py-4">
                          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                            <div>
                              <p className="text-xs text-gray-600 uppercase tracking-wider mb-1.5">Input</p>
                              <pre className="text-xs text-gray-400 whitespace-pre-wrap font-mono bg-gray-900 rounded p-3">
                                {JSON.stringify(c.input_params, null, 2)}
                              </pre>
                            </div>
                            <div>
                              <p className="text-xs text-gray-600 uppercase tracking-wider mb-1.5">Output</p>
                              <pre className="text-xs text-gray-400 whitespace-pre-wrap font-mono bg-gray-900 rounded p-3">
                                {JSON.stringify(c.output, null, 2)}
                              </pre>
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {callsLoaded && calls.length === 0 && (
        <p className="text-xs text-gray-600 py-4">No agent calls recorded for this MCP.</p>
      )}

      {!callsLoaded && mcp.healthy && (
        <p className="text-xs text-gray-600 py-4">Loading calls...</p>
      )}
    </div>
  );
}

export default function DashboardPage() {
  const router = useRouter();
  const { apiFetch } = useApi();
  const [data, setData] = useState<DashboardData | null>(null);
  const [activeTab, setActiveTab] = useState<string>("");
  const [callsCache, setCallsCache] = useState<Record<string, CallRecord[]>>({});
  const [loadedTabs, setLoadedTabs] = useState<Set<string>>(new Set());
  const [source, setSource] = useState<string>("all");
  const [dateFrom, setDateFrom] = useState<string>("");

  function filterParams() {
    const p = new URLSearchParams();
    if (source !== "all") p.set("source", source);
    if (dateFrom) p.set("date_from", dateFrom);
    return p.toString() ? `&${p.toString()}` : "";
  }

  const loadCalls = useCallback(async (mcp: string) => {
    if (loadedTabs.has(mcp)) return;
    const rows = await apiFetch<CallRecord[]>(`${BACKEND}/api/agent/dashboard/calls/?mcp=${mcp}${filterParams()}`);
    setCallsCache((prev) => ({ ...prev, [mcp]: Array.isArray(rows) ? rows : [] }));
    setLoadedTabs((prev) => new Set([...prev, mcp]));
  }, [loadedTabs, source, dateFrom]);

  function reloadAll(newSource = source, newDateFrom = dateFrom) {
    setCallsCache({});
    setLoadedTabs(new Set());
    const p = new URLSearchParams();
    if (newSource !== "all") p.set("source", newSource);
    if (newDateFrom) p.set("date_from", newDateFrom);
    const params = p.toString() ? `?${p.toString()}` : "";
    apiFetch<DashboardData>(`${BACKEND}/api/agent/dashboard/${params}`)
      .then((d) => {
        if (!d || !d.mcps) return;
        setData(d);
      })
      .catch(() => {});
  }

  useEffect(() => {
    if (!localStorage.getItem("access_token")) { router.replace("/login"); return; }
    // if (localStorage.getItem("user_role") !== "admin") { router.replace("/"); return; }
    apiFetch<DashboardData>(`${BACKEND}/api/agent/dashboard/`)
      .then((d) => {
        if (!d || !d.mcps) return;
        setData(d);
        const first = d.mcps.find((m) => m.healthy)?.name ?? d.mcps[0]?.name ?? "";
        setActiveTab(first);
        if (first) loadCalls(first);
      })
      .catch(() => {});
  }, [router]);

  useEffect(() => {
    if (activeTab) loadCalls(activeTab);
  }, [activeTab, loadCalls]);

  if (!data) {
    return (
      <div className="h-full bg-gray-950 text-gray-100 flex items-center justify-center">
        <p className="text-xs text-gray-600">Loading dashboard...</p>
      </div>
    );
  }

  const activeMcp = data.mcps?.find((m) => m.name === activeTab);

  return (
    <div className="h-full bg-gray-950 text-gray-100">
      {/* <div className="flex items-center gap-4 px-6 py-3 border-b border-gray-800 text-sm">
        Chat / Dashboard
      </div> */}

      <div className="flex flex-1 h-full">
        <aside className="w-48 shrink-0 border-r border-gray-800 py-4 flex flex-col gap-1 px-2">
          {data.mcps.map((m) => (
            <button
              key={m.name}
              onClick={() => m.healthy && setActiveTab(m.name)}
              className={`flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-colors ${
                activeTab === m.name
                  ? "bg-gray-800 text-gray-100"
                  : m.healthy
                  ? "text-gray-400 hover:bg-gray-900 hover:text-gray-200"
                  : "text-gray-700 cursor-default"
              }`}
            >
              <span className="capitalize">{m.name}</span>
              <span
                className={`w-1.5 h-1.5 rounded-full shrink-0 ${m.healthy ? "bg-green-500" : "bg-red-700"}`}
              />
            </button>
          ))}
        </aside>

        <main className="flex-1 overflow-y-auto px-8 py-6">
          <div className="flex items-center gap-3 mb-5 flex-wrap">
            <div className="flex gap-1">
              {["all", "web", "discord", "telegram"].map(s => (
                <button
                  key={s}
                  onClick={() => { setSource(s); reloadAll(s, dateFrom); }}
                  className={`text-xs px-2.5 py-1 rounded capitalize transition-colors ${source === s ? "bg-blue-600 text-white" : "text-gray-500 hover:text-gray-300 border border-gray-800"}`}
                >{s}</button>
              ))}
            </div>
            <input
              type="date"
              value={dateFrom}
              onChange={e => { setDateFrom(e.target.value); reloadAll(source, e.target.value); }}
              className="text-xs bg-gray-900 border border-gray-800 rounded px-2 py-1 text-gray-400 focus:outline-none"
            />
            {dateFrom && (
              <button onClick={() => { setDateFrom(""); reloadAll(source, ""); }} className="text-xs text-gray-600 hover:text-gray-400">Clear</button>
            )}
          </div>

          {activeMcp ? (
            <>
              <div className="flex items-center gap-3 mb-6">
                <h1 className="text-lg font-semibold capitalize text-gray-100">{activeMcp.name}</h1>
                <span
                  className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                    activeMcp.healthy
                      ? "bg-green-950 text-green-400 border border-green-900"
                      : "bg-red-950 text-red-400 border border-red-900"
                  }`}
                >
                  {activeMcp.healthy ? "online" : "offline"}
                </span>
                {data.agent_calls[activeMcp.name] && (
                  <span className="text-xs text-gray-600 ml-auto">
                    {data.agent_calls[activeMcp.name].total} total call{data.agent_calls[activeMcp.name].total !== 1 ? "s" : ""}
                  </span>
                )}
              </div>
              <McpPanel
                mcp={activeMcp}
                calls={callsCache[activeMcp.name] ?? []}
                callsLoaded={loadedTabs.has(activeMcp.name)}
              />
            </>
          ) : (
            <p className="text-xs text-gray-600 py-8 text-center">No MCP servers configured.</p>
          )}
        </main>
      </div>
    </div>
  );
}
