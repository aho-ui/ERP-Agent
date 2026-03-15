"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

const BACKEND = "http://localhost:8000";

type ArtifactItem =
  | { artifact_type: "table"; columns: string[]; rows: unknown[][] }
  | { artifact_type: "chart"; image: string; title: string }
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

export default function LogsPage() {
  const router = useRouter();
  const [logs, setLogs] = useState<LogRow[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [lightbox, setLightbox] = useState<{ image: string; title: string } | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) { router.replace("/login"); return; }
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
                                {artifact.artifact_type === "chart" && (
                                  <div className="p-2 flex items-start gap-3">
                                    <img
                                      src={(artifact as { artifact_type: "chart"; image: string; title: string }).image}
                                      alt={(artifact as { artifact_type: "chart"; image: string; title: string }).title}
                                      className="w-64 rounded shrink-0 cursor-zoom-in"
                                      onClick={() => setLightbox({ image: (artifact as { artifact_type: "chart"; image: string; title: string }).image, title: (artifact as { artifact_type: "chart"; image: string; title: string }).title })}
                                    />
                                    <div className="flex flex-col gap-1 pt-1">
                                      {(artifact as { artifact_type: "chart"; image: string; title: string }).title && (
                                        <p className="text-xs text-gray-300">{(artifact as { artifact_type: "chart"; image: string; title: string }).title}</p>
                                      )}
                                      <a
                                        href={(artifact as { artifact_type: "chart"; image: string; title: string }).image}
                                        download={(artifact as { artifact_type: "chart"; image: string; title: string }).title || "chart.png"}
                                        className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
                                      >
                                        Download PNG
                                      </a>
                                    </div>
                                  </div>
                                )}
                                {artifact.artifact_type === "table" && (() => {
                                  const t = artifact as { artifact_type: "table"; columns: string[]; rows: unknown[][] };
                                  return (
                                    <div className="overflow-x-auto">
                                      <table className="w-full text-xs text-left text-gray-300">
                                        <thead className="bg-gray-800 text-gray-400 uppercase">
                                          <tr>
                                            {t.columns.map((col) => (
                                              <th key={col} className="px-3 py-2 font-medium whitespace-nowrap">{col}</th>
                                            ))}
                                          </tr>
                                        </thead>
                                        <tbody>
                                          {t.rows.map((row, ri) => (
                                            <tr key={ri} className="border-t border-gray-700">
                                              {(row as unknown[]).map((cell, ci) => (
                                                <td key={ci} className="px-3 py-2 whitespace-nowrap">
                                                  {cell === null || cell === undefined ? "—" : String(cell)}
                                                </td>
                                              ))}
                                            </tr>
                                          ))}
                                        </tbody>
                                      </table>
                                    </div>
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

      {lightbox && (
        <div
          className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-6"
          onClick={() => setLightbox(null)}
        >
          <div className="max-w-4xl w-full" onClick={(e) => e.stopPropagation()}>
            {lightbox.title && <p className="text-xs text-gray-400 mb-2">{lightbox.title}</p>}
            <img src={lightbox.image} alt={lightbox.title} className="w-full rounded" />
            <button
              className="mt-3 text-xs text-gray-500 hover:text-gray-300 transition-colors"
              onClick={() => setLightbox(null)}
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
