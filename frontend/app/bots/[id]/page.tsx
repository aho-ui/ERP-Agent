"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import Link from "next/link";
import { useRouter, useParams } from "next/navigation";
import { useApi, BACKEND } from "../../lib/api";

type Bot = { id: string; name: string; platform: string; role: string; is_active: boolean; running: boolean };
type BotSession = { id: string; label: string; updated_at: string };
type Message = { id: string; role: string; content: string; timestamp: string };

// const BACKEND = "http://localhost:8000";

export default function BotDetailPage() {
  const router = useRouter();
  const { apiFetch, authHeader } = useApi();
  const { id: botId } = useParams<{ id: string }>();
  const [bot, setBot] = useState<Bot | null>(null);
  const [sessions, setSessions] = useState<BotSession[]>([]);
  const [activeSession, setActiveSession] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  // const [pendingStep, setPendingStep] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // function authHeader() { ... } — moved to useApi

  useEffect(() => {
    if (!localStorage.getItem("access_token")) { router.replace("/login"); return; }
    if (localStorage.getItem("user_role") !== "admin") { router.replace("/"); return; }
    apiFetch<Bot[]>(`${BACKEND}/api/agent/bots/`)
      .then(data => {
        if (!data) return;
        const found = data.find((b: Bot) => b.id === botId);
        if (found) setBot(found);
      })
      .catch(() => {});

    apiFetch<BotSession[]>(`${BACKEND}/api/agent/bots/${botId}/sessions/`)
      .then(data => data && setSessions(data))
      .catch(() => {});
  }, [botId, router]);

  const fetchMessages = useCallback((sessionId: string) => {
    apiFetch<Message[]>(`${BACKEND}/api/agent/sessions/${sessionId}/messages/`)
      .then(data => {
        if (!data) return;
        setMessages(data);
        setTimeout(() => messagesEndRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
      })
      .catch(() => {});
  }, []);

  async function exportSession(fmt: "csv" | "pdf") {
    const exportable = messages.filter(m => !m.content.startsWith("[thinking] "));
    const columns = ["Role", "Content", "Time"];
    const rows = exportable.map(m => [
      m.role,
      m.content,
      new Date(m.timestamp).toLocaleString(),
    ]);
    const session = sessions.find(s => s.id === activeSession);
    const title = session?.label ?? "bot-session";
    const res = await fetch(`${BACKEND}/api/agent/export/${fmt}/`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeader() },
      body: JSON.stringify({ format: fmt, columns, rows, title }),
    });
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `${title}.${fmt}`; a.click();
    URL.revokeObjectURL(url);
  }

  useEffect(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    if (!activeSession) return;
    fetchMessages(activeSession);
    pollRef.current = setInterval(() => fetchMessages(activeSession), 3000);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [activeSession, fetchMessages]);

  // useEffect(() => {
  //   if (!botId) return;
  //   const controller = new AbortController();
  //   (async () => {
  //     try {
  //       const res = await fetch(`${BACKEND}/api/agent/bots/${botId}/progress/`, {
  //         headers: authHeader(),
  //         signal: controller.signal,
  //       });
  //       if (!res.ok || !res.body) return;
  //       const reader = res.body.getReader();
  //       const decoder = new TextDecoder();
  //       let buffer = "";
  //       while (true) {
  //         const { done, value } = await reader.read();
  //         if (done) break;
  //         buffer += decoder.decode(value, { stream: true });
  //         const lines = buffer.split("\n");
  //         buffer = lines.pop() ?? "";
  //         for (const line of lines) {
  //           if (!line.startsWith("data: ")) continue;
  //           const raw = line.slice(6).trim();
  //           if (raw === "[DONE]" || raw === "[KEEPALIVE]") { setPendingStep(null); continue; }
  //           try {
  //             const event = JSON.parse(raw);
  //             if (event.type === "progress") setPendingStep(event.content);
  //             else if (event.type === "response") setPendingStep(null);
  //           } catch {}
  //         }
  //       }
  //     } catch {}
  //   })();
  //   return () => controller.abort();
  // }, [botId]);

  return (
    <div className="h-full flex flex-col bg-gray-950 text-gray-100">
      {/* <div className="flex items-center gap-3 px-4 py-2 border-b border-gray-800 text-xs">
        Chat | Agents | Bots | {bot?.name}
      </div> */}

      <div className="flex flex-1 min-h-0">
        <div className="w-56 border-r border-gray-800 flex flex-col">
          <p className="text-[10px] text-gray-600 font-medium px-3 pt-3 pb-2 uppercase tracking-wider">Sessions</p>
          <div className="flex-1 overflow-y-auto">
            {sessions.length === 0 && (
              <p className="text-xs text-gray-700 px-3 py-4">No sessions yet.</p>
            )}
            {sessions.map(s => (
              <button
                key={s.id}
                onClick={() => setActiveSession(s.id)}
                className={`w-full text-left px-3 py-2.5 border-b border-gray-900 transition-colors ${
                  activeSession === s.id ? "bg-gray-800 text-gray-200" : "text-gray-400 hover:bg-gray-900 hover:text-gray-200"
                }`}
              >
                <p className="text-xs truncate">{s.label}</p>
                <p className="text-[10px] text-gray-600 mt-0.5">{new Date(s.updated_at).toLocaleDateString()}</p>
              </button>
            ))}
          </div>
        </div>

        <div className="flex-1 flex flex-col min-h-0">
          {activeSession && messages.length > 0 && (
            <div className="flex items-center gap-2 px-4 py-2 border-b border-gray-800 shrink-0">
              <span className="text-[10px] text-gray-600 uppercase tracking-wider ml-auto">Export</span>
              <button onClick={() => exportSession("csv")} className="text-xs text-gray-400 hover:text-gray-200 border border-gray-700 px-2.5 py-1 rounded transition-colors">CSV</button>
              <button onClick={() => exportSession("pdf")} className="text-xs text-gray-400 hover:text-gray-200 border border-gray-700 px-2.5 py-1 rounded transition-colors">PDF</button>
            </div>
          )}
          {!activeSession ? (
            <div className="flex-1 flex items-center justify-center">
              <p className="text-xs text-gray-700">Select a session to view messages.</p>
            </div>
          ) : (
            <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
              {messages.map(m => {
                const isThinking = m.role === "assistant" && m.content.startsWith("[thinking] ");
                if (isThinking) {
                  return (
                    <div key={m.id} className="flex justify-start">
                      <p className="text-[11px] italic text-gray-600 px-1">{m.content.slice(11)}</p>
                    </div>
                  );
                }
                return (
                  <div key={m.id} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                    <div className={`max-w-[70%] px-3 py-2 rounded-xl text-sm ${
                      m.role === "user"
                        ? "bg-blue-600 text-white"
                        : "bg-gray-800 text-gray-200"
                    }`}>
                      <p className="whitespace-pre-wrap">{m.content}</p>
                      <p className="text-[10px] opacity-50 mt-1">{new Date(m.timestamp).toLocaleTimeString()}</p>
                    </div>
                  </div>
                );
              })}
              {/* pendingStep UI — reserved for future use */}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
