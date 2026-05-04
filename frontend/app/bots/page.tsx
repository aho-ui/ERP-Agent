"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useApi, BACKEND } from "../lib/api";

type Bot = { id: string; name: string; platform: string; role: string; is_active: boolean; running: boolean; webhook_url?: string | null };

// const BACKEND = "http://localhost:8000";

const PLATFORMS = [
  { value: "discord", label: "Discord" },
  { value: "telegram", label: "Telegram" },
  { value: "whatsapp", label: "WhatsApp" },
  { value: "slack", label: "Slack" },
];

const ROLES = [
  { value: "viewer", label: "Viewer" },
  { value: "admin", label: "Admin" },
];

export default function BotsPage() {
  const router = useRouter();
  const { apiFetch } = useApi();
  const [bots, setBots] = useState<Bot[]>([]);
  const [formOpen, setFormOpen] = useState(false);
  const [name, setName] = useState("");
  const [platform, setPlatform] = useState("discord");
  const [role, setRole] = useState("viewer");
  const [token, setToken] = useState("");
  const [accountSid, setAccountSid] = useState("");
  const [authToken, setAuthToken] = useState("");
  const [fromNumber, setFromNumber] = useState("");
  const [slackBotToken, setSlackBotToken] = useState("");
  const [slackAppToken, setSlackAppToken] = useState("");
  const [saving, setSaving] = useState(false);
  const [toggling, setToggling] = useState<string | null>(null);
  const [changingRole, setChangingRole] = useState<string | null>(null);
  const [copied, setCopied] = useState<string | null>(null);

  // function authHeader() { ... } — moved to useApi

  useEffect(() => {
    if (!localStorage.getItem("access_token")) { router.replace("/login"); return; }
    if (localStorage.getItem("user_role") !== "admin") { router.replace("/"); return; }
    fetchBots();
  }, [router]);

  function fetchBots() {
    apiFetch<Bot[]>(`${BACKEND}/api/agent/bots/`)
      .then(data => data && setBots(data))
      .catch(() => {});
  }

  async function createBot() {
    if (!name.trim()) return;
    const resolvedToken = platform === "whatsapp"
      ? JSON.stringify({ account_sid: accountSid.trim(), auth_token: authToken.trim(), from: fromNumber.trim() })
      : platform === "slack"
      ? JSON.stringify({ bot_token: slackBotToken.trim(), app_token: slackAppToken.trim() })
      : token.trim();
    if (!resolvedToken) return;
    setSaving(true);
    const res = await apiFetch<Bot>(`${BACKEND}/api/agent/bots/`, {
      method: "POST",
      body: JSON.stringify({ name: name.trim(), platform, role, token: resolvedToken }),
    });
    if (res) {
      setBots(prev => [...prev, res]);
      setName("");
      setPlatform("discord");
      setRole("viewer");
      setToken("");
      setAccountSid("");
      setAuthToken("");
      setFromNumber("");
      setSlackBotToken("");
      setSlackAppToken("");
      setFormOpen(false);
    }
    setSaving(false);
  }

  async function toggle(bot: Bot) {
    setToggling(bot.id);
    await apiFetch<{ running: boolean }>(`${BACKEND}/api/agent/bots/${bot.id}/`, {
      method: "PATCH",
      body: JSON.stringify({ is_active: !bot.is_active }),
    });
    fetchBots();
    setToggling(null);
  }

  async function changeRole(bot: Bot, newRole: string) {
    setChangingRole(bot.id);
    const data = await apiFetch(`${BACKEND}/api/agent/bots/${bot.id}/`, {
      method: "PATCH",
      body: JSON.stringify({ role: newRole }),
    });
    if (data) {
      setBots(prev => prev.map(b => b.id === bot.id ? { ...b, role: newRole } : b));
    }
    setChangingRole(null);
  }

  async function deleteBot(id: string) {
    await apiFetch(`${BACKEND}/api/agent/bots/${id}/`, { method: "DELETE" });
    setBots(prev => prev.filter(b => b.id !== id));
  }

  function copyUrl(url: string, id: string) {
    navigator.clipboard.writeText(url);
    setCopied(id);
    setTimeout(() => setCopied(null), 2000);
  }

  const isWhatsApp = platform === "whatsapp";
  const isSlack = platform === "slack";
  const createDisabled = saving || !name.trim() || (
    isWhatsApp ? (!accountSid.trim() || !authToken.trim() || !fromNumber.trim()) :
    isSlack ? (!slackBotToken.trim() || !slackAppToken.trim()) :
    !token.trim()
  );

  return (
    <div className="h-full overflow-y-auto bg-gray-950 text-gray-100">
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
            {isSlack ? (
              <>
                <input
                  className="w-full bg-gray-800 rounded-lg px-3 py-2 text-sm outline-none placeholder-gray-500 focus:ring-1 focus:ring-blue-600 font-mono"
                  placeholder="Bot Token (xoxb-...)"
                  value={slackBotToken}
                  onChange={e => setSlackBotToken(e.target.value)}
                  type="password"
                />
                <input
                  className="w-full bg-gray-800 rounded-lg px-3 py-2 text-sm outline-none placeholder-gray-500 focus:ring-1 focus:ring-blue-600 font-mono"
                  placeholder="App Token (xapp-...)"
                  value={slackAppToken}
                  onChange={e => setSlackAppToken(e.target.value)}
                  type="password"
                />
              </>
            ) : isWhatsApp ? (
              <>
                <input
                  className="w-full bg-gray-800 rounded-lg px-3 py-2 text-sm outline-none placeholder-gray-500 focus:ring-1 focus:ring-blue-600 font-mono"
                  placeholder="Account SID"
                  value={accountSid}
                  onChange={e => setAccountSid(e.target.value)}
                />
                <input
                  className="w-full bg-gray-800 rounded-lg px-3 py-2 text-sm outline-none placeholder-gray-500 focus:ring-1 focus:ring-blue-600 font-mono"
                  placeholder="Auth Token"
                  value={authToken}
                  onChange={e => setAuthToken(e.target.value)}
                  type="password"
                />
                <input
                  className="w-full bg-gray-800 rounded-lg px-3 py-2 text-sm outline-none placeholder-gray-500 focus:ring-1 focus:ring-blue-600 font-mono"
                  placeholder="From number (e.g. whatsapp:+14155238886)"
                  value={fromNumber}
                  onChange={e => setFromNumber(e.target.value)}
                />
              </>
            ) : (
              <input
                className="w-full bg-gray-800 rounded-lg px-3 py-2 text-sm outline-none placeholder-gray-500 focus:ring-1 focus:ring-blue-600 font-mono"
                placeholder={platform === "discord" ? "Discord bot token" : "Telegram bot token"}
                value={token}
                onChange={e => setToken(e.target.value)}
                type="password"
              />
            )}
            <button
              className="w-full px-3 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-sm font-medium disabled:opacity-40 transition-colors"
              onClick={createBot}
              disabled={createDisabled}
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
            <div key={bot.id} className="bg-gray-900 border border-gray-800 rounded-xl px-4 py-3 space-y-2">
              <div className="flex items-center gap-3">
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
              {bot.platform === "whatsapp" && bot.is_active && bot.webhook_url && (
                <div className="flex items-center gap-2 bg-gray-800 rounded-lg px-3 py-2">
                  <span className="text-[10px] text-gray-500 shrink-0">Webhook</span>
                  <span className="text-[10px] font-mono text-gray-300 truncate flex-1">{bot.webhook_url}</span>
                  <button
                    onClick={() => copyUrl(bot.webhook_url!, bot.id)}
                    className="text-[10px] text-gray-500 hover:text-gray-200 shrink-0 transition-colors"
                  >
                    {copied === bot.id ? "copied" : "copy"}
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
