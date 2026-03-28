"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import Link from "next/link";
import { useRouter, useParams } from "next/navigation";

type Bot = { id: string; name: string; platform: string; role: string; is_active: boolean; running: boolean };
type BotSession = { id: string; label: string; updated_at: string };
type Message = { id: string; role: string; content: string; timestamp: string };

const BACKEND = "http://localhost:8000";

export default function BotDetailPage() {
  const router = useRouter();
  const { id: botId } = useParams<{ id: string }>();
  const [bot, setBot] = useState<Bot | null>(null);
  const [sessions, setSessions] = useState<BotSession[]>([]);
  const [activeSession, setActiveSession] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  function authHeader() {
    return { "Authorization": `Bearer ${localStorage.getItem("access_token") ?? ""}` };
  }

  useEffect(() => {
    if (!localStorage.getItem("access_token")) { router.replace("/login"); return; }
    fetch(`${BACKEND}/api/agent/bots/`, { headers: authHeader() })
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (!data) return;
        const found = data.find((b: Bot) => b.id === botId);
        if (found) setBot(found);
      })
      .catch(() => {});

    fetch(`${BACKEND}/api/agent/bots/${botId}/sessions/`, { headers: authHeader() })
      .then(r => r.ok ? r.json() : [])
      .then(setSessions)
      .catch(() => {});
  }, [botId, router]);

  const fetchMessages = useCallback((sessionId: string) => {
    fetch(`${BACKEND}/api/agent/sessions/${sessionId}/messages/`, { headers: authHeader() })
      .then(r => r.ok ? r.json() : [])
      .then((data: Message[]) => {
        setMessages(data);
        setTimeout(() => messagesEndRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    if (!activeSession) return;
    fetchMessages(activeSession);
    pollRef.current = setInterval(() => fetchMessages(activeSession), 3000);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [activeSession, fetchMessages]);

  async function sendMessage() {
    if (!input.trim() || !activeSession || sending) return;
    setSending(true);
    const res = await fetch(`${BACKEND}/api/agent/bots/${botId}/sessions/${activeSession}/chat/`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeader() },
      body: JSON.stringify({ content: input.trim() }),
    });
    if (res.ok) {
      setInput("");
      fetchMessages(activeSession);
      fetch(`${BACKEND}/api/agent/bots/${botId}/sessions/`, { headers: authHeader() })
        .then(r => r.ok ? r.json() : [])
        .then(setSessions)
        .catch(() => {});
    }
    setSending(false);
  }

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <div className="flex items-center gap-3 px-4 py-2 border-b border-gray-800 text-xs">
        <Link href="/" className="text-gray-400 hover:text-gray-200 transition-colors font-medium">Chat</Link>
        <span className="text-gray-700">|</span>
        <Link href="/agents" className="text-gray-400 hover:text-gray-200 transition-colors font-medium">Agents</Link>
        <span className="text-gray-700">|</span>
        <Link href="/bots" className="text-gray-400 hover:text-gray-200 transition-colors font-medium">Bots</Link>
        <span className="text-gray-700">|</span>
        <span className="text-gray-300 font-medium">{bot?.name ?? "..."}</span>
      </div>

      <div className="flex h-[calc(100vh-33px)]">
        {/* sessions sidebar */}
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

        {/* message view */}
        <div className="flex-1 flex flex-col">
          {!activeSession ? (
            <div className="flex-1 flex items-center justify-center">
              <p className="text-xs text-gray-700">Select a session to view messages.</p>
            </div>
          ) : (
            <>
              <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
                {messages.map(m => (
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
                ))}
                <div ref={messagesEndRef} />
              </div>

              {/* manual override input */}
              <div className="border-t border-gray-800 px-4 py-3 flex gap-2">
                <input
                  className="flex-1 bg-gray-900 border border-gray-800 rounded-lg px-3 py-2 text-sm outline-none placeholder-gray-600 focus:ring-1 focus:ring-blue-600"
                  placeholder="Send override message..."
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
                  disabled={sending}
                />
                <button
                  onClick={sendMessage}
                  disabled={sending || !input.trim()}
                  className="px-3 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-xs font-medium disabled:opacity-40 transition-colors"
                >
                  {sending ? "..." : "Send"}
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
