"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

type Bot = { id: string; name: string; platform: string; role: string; is_active: boolean; running: boolean };

const BACKEND = "http://localhost:8000";

const PLATFORMS = [
  { value: "discord", label: "Discord" },
  { value: "telegram", label: "Telegram" },
];

const ROLES = [
  { value: "viewer", label: "Viewer" },
  { value: "admin", label: "Admin" },
];

export default function BotsPage() {
  const router = useRouter();
  const [bots, setBots] = useState<Bot[]>([]);
  const [formOpen, setFormOpen] = useState(false);
  const [name, setName] = useState("");
  const [platform, setPlatform] = useState("discord");
  const [role, setRole] = useState("viewer");
  const [token, setToken] = useState("");
  const [saving, setSaving] = useState(false);
  const [toggling, setToggling] = useState<string | null>(null);
  const [changingRole, setChangingRole] = useState<string | null>(null);

  function authHeader() {
    return { "Authorization": `Bearer ${localStorage.getItem("access_token") ?? ""}` };
  }

  useEffect(() => {
    if (!localStorage.getItem("access_token")) { router.replace("/login"); return; }
    fetch(`${BACKEND}/api/agent/bots/`, { headers: authHeader() })
      .then(r => r.ok ? r.json() : [])
      .then(setBots)
      .catch(() => {});
  }, [router]);

  async function createBot() {
    if (!name.trim() || !token.trim()) return;
    setSaving(true);
    const res = await fetch(`${BACKEND}/api/agent/bots/create/`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeader() },
      body: JSON.stringify({ name: name.trim(), platform, role, token: token.trim() }),
    });
    if (res.ok) {
      const bot = await res.json() as Bot;
      setBots(prev => [...prev, bot]);
      setName("");
      setPlatform("discord");
      setRole("viewer");
      setToken("");
      setFormOpen(false);
    }
    setSaving(false);
  }

  async function toggle(bot: Bot) {
    setToggling(bot.id);
    const res = await fetch(`${BACKEND}/api/agent/bots/${bot.id}/`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json", ...authHeader() },
      body: JSON.stringify({ is_active: !bot.is_active }),
    });
    if (res.ok) {
      const data = await res.json() as { running: boolean };
      setBots(prev => prev.map(b => b.id === bot.id ? { ...b, is_active: !bot.is_active, running: data.running } : b));
    }
    setToggling(null);
  }

  async function changeRole(bot: Bot, newRole: string) {
    setChangingRole(bot.id);
    const res = await fetch(`${BACKEND}/api/agent/bots/${bot.id}/`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json", ...authHeader() },
      body: JSON.stringify({ role: newRole }),
    });
    if (res.ok) {
      setBots(prev => prev.map(b => b.id === bot.id ? { ...b, role: newRole } : b));
    }
    setChangingRole(null);
  }

  async function deleteBot(id: string) {
    await fetch(`${BACKEND}/api/agent/bots/${id}/`, { method: "DELETE", headers: authHeader() });
    setBots(prev => prev.filter(b => b.id !== id));
  }

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <div className="flex items-center gap-3 px-4 py-2 border-b border-gray-800 text-xs">
        <Link href="/" className="text-gray-400 hover:text-gray-200 transition-colors font-medium">Chat</Link>
        <span className="text-gray-700">|</span>
        <Link href="/agents" className="text-gray-400 hover:text-gray-200 transition-colors font-medium">Agents</Link>
        <span className="text-gray-700">|</span>
        <span className="text-gray-300 font-medium">Bots</span>
      </div>

      <div className="max-w-2xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-sm font-medium text-gray-300">Platform Bots</h1>
          <button
            className="text-xs px-3 py-1.5 bg-blue-600 hover:bg-blue-500 rounded-lg transition-colors"
            onClick={() => setFormOpen(v => !v)}
          >
            {formOpen ? "Cancel" : "Add Bot"}
          </button>
        </div>

        {formOpen && (
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 mb-4 space-y-3">
            <input
              className="w-full bg-gray-800 rounded-lg px-3 py-2 text-sm outline-none placeholder-gray-500 focus:ring-1 focus:ring-blue-600"
              placeholder="Bot name"
              value={name}
              onChange={e => setName(e.target.value)}
            />
            <div className="flex gap-2">
              {PLATFORMS.map(p => (
                <button
                  key={p.value}
                  className={`flex-1 px-3 py-2 rounded-lg text-xs font-medium border transition-colors ${
                    platform === p.value
                      ? "bg-blue-600 border-blue-600 text-white"
                      : "bg-gray-800 border-gray-700 text-gray-400 hover:text-gray-200"
                  }`}
                  onClick={() => setPlatform(p.value)}
                >
                  {p.label}
                </button>
              ))}
            </div>
            <div className="flex gap-2">
              {ROLES.map(r => (
                <button
                  key={r.value}
                  className={`flex-1 px-3 py-2 rounded-lg text-xs font-medium border transition-colors ${
                    role === r.value
                      ? "bg-blue-600 border-blue-600 text-white"
                      : "bg-gray-800 border-gray-700 text-gray-400 hover:text-gray-200"
                  }`}
                  onClick={() => setRole(r.value)}
                >
                  {r.label}
                </button>
              ))}
            </div>
            <input
              className="w-full bg-gray-800 rounded-lg px-3 py-2 text-sm outline-none placeholder-gray-500 focus:ring-1 focus:ring-blue-600 font-mono"
              placeholder={platform === "discord" ? "Discord bot token" : "Telegram bot token"}
              value={token}
              onChange={e => setToken(e.target.value)}
              type="password"
            />
            <button
              className="w-full px-3 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-sm font-medium disabled:opacity-40 transition-colors"
              onClick={createBot}
              disabled={saving || !name.trim() || !token.trim()}
            >
              {saving ? "Creating..." : "Create Bot"}
            </button>
          </div>
        )}

        <div className="space-y-2">
          {bots.length === 0 && (
            <p className="text-xs text-gray-600 text-center py-8">No bots yet.</p>
          )}
          {bots.map(bot => (
            <div key={bot.id} className="flex items-center gap-3 bg-gray-900 border border-gray-800 rounded-xl px-4 py-3">
              <div className="flex-1 min-w-0">
                <Link href={`/bots/${bot.id}`} className="text-sm text-gray-200 hover:text-white truncate block">{bot.name}</Link>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="text-xs text-gray-500 capitalize">{bot.platform}</span>
                  <div className="flex gap-1">
                    {ROLES.map(r => (
                      <button
                        key={r.value}
                        disabled={changingRole === bot.id}
                        onClick={() => bot.role !== r.value && changeRole(bot, r.value)}
                        className={`text-[10px] px-1.5 py-0.5 rounded transition-colors disabled:opacity-40 ${
                          bot.role === r.value
                            ? "bg-blue-900/50 text-blue-400"
                            : "text-gray-600 hover:text-gray-400"
                        }`}
                      >
                        {r.label}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                {bot.is_active && (
                  <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full ${bot.running ? "bg-green-900/40 text-green-400" : "bg-yellow-900/40 text-yellow-400"}`}>
                    {bot.running ? "running" : "starting"}
                  </span>
                )}
                <button
                  onClick={() => toggle(bot)}
                  disabled={toggling === bot.id}
                  className={`relative w-10 h-5 rounded-full transition-colors duration-200 focus:outline-none disabled:opacity-50 ${bot.is_active ? "bg-blue-600" : "bg-gray-700"}`}
                >
                  <span className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white transition-transform duration-200 ${bot.is_active ? "translate-x-5" : "translate-x-0"}`} />
                </button>
                <button
                  onClick={() => deleteBot(bot.id)}
                  className="text-xs text-gray-600 hover:text-red-400 transition-colors"
                >
                  ×
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
