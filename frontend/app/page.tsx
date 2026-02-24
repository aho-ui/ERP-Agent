"use client";

import { useState, useRef, useEffect } from "react";

type Message = { role: "user" | "assistant"; content: string };
type LogEntry = { content: string; timestamp: string };

const BACKEND = "http://localhost:8000";

export default function Page() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const chatEndRef = useRef<HTMLDivElement>(null);
  const logEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);
  useEffect(() => { logEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [logs]);

  async function send() {
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput("");
    setLoading(true);
    setLogs([]);
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);

    const res = await fetch(`${BACKEND}/api/agent/chat/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: userMessage }),
    });

    const reader = res.body!.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

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
          setLogs((prev) => [...prev, { content: event.content, timestamp: new Date().toLocaleTimeString() }]);
        } else if (event.type === "response") {
          setMessages((prev) => [...prev, { role: "assistant", content: event.content }]);
        }
      }
    }

    setLoading(false);
  }

  return (
    <div className="flex h-screen bg-gray-950 text-gray-100">
      <div className="flex flex-col flex-1 border-r border-gray-800">
        <div className="px-4 py-3 border-b border-gray-800 text-sm font-medium text-gray-400">Chat</div>

        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[75%] rounded-lg px-4 py-2 text-sm whitespace-pre-wrap ${
                m.role === "user" ? "bg-blue-600 text-white" : "bg-gray-800 text-gray-100"
              }`}>
                {m.content}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="bg-gray-800 rounded-lg px-4 py-2 text-sm text-gray-400">Thinking...</div>
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
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-2 font-mono">
          {logs.length === 0 && (
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
  );
}
