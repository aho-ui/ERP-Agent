"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

type AgentItem = {
  id: string | null;
  name: string;
  type: string;
  instructions?: string;
  system_prompt?: string;
  description?: string;
  allowed_tools: string[];
  builtin: boolean;
  is_active: boolean;
  created_at?: string;
};

const BACKEND = "http://localhost:8000";

function toolLabel(t: string) {
  return t.replace("mcp_odoo_", "").replace(/_/g, " ");
}

export default function AgentsPage() {
  const router = useRouter();

  useEffect(() => {
    if (!localStorage.getItem("access_token")) { router.replace("/login"); return; }
    setUserRole(localStorage.getItem("user_role") ?? "");
  }, [router]);

  function authHeader() {
    const token = localStorage.getItem("access_token") ?? "";
    return { "Authorization": `Bearer ${token}` };
  }

  const [userRole, setUserRole] = useState<string>("");
  const [agents, setAgents] = useState<AgentItem[]>([]);
  const [tools, setTools] = useState<string[]>([]);
  const [selected, setSelected] = useState<AgentItem | null>(null);
  const [creating, setCreating] = useState(false);

  const [fName, setFName] = useState("");
  const [fType, setFType] = useState("");
  const [fInstructions, setFInstructions] = useState("");
  const [fTools, setFTools] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [toggling, setToggling] = useState<string | null>(null);

  useEffect(() => {
    fetchAgents();
    fetchTools();
  }, []);

  async function fetchAgents() {
    try {
      const res = await fetch(`${BACKEND}/api/agent/templates/`, { headers: authHeader() });
      setAgents(await res.json());
    } catch {}
  }

  async function fetchTools() {
    try {
      const res = await fetch(`${BACKEND}/api/agent/templates/tools/`, { headers: authHeader() });
      setTools(await res.json());
    } catch {}
  }

  function openCreate() {
    setSelected(null);
    setFName("");
    setFType("");
    setFInstructions("");
    setFTools([]);
    setCreating(true);
  }

  function openEdit(agent: AgentItem) {
    setCreating(false);
    setSelected(agent);
    setFName(agent.name);
    setFType(agent.type === "builtin" ? "" : agent.type);
    setFInstructions(agent.instructions ?? "");
    setFTools(agent.allowed_tools);
  }

  function closeForm() {
    setCreating(false);
    setSelected(null);
  }

  function toggleTool(tool: string) {
    setFTools(prev => prev.includes(tool) ? prev.filter(t => t !== tool) : [...prev, tool]);
  }

  async function save() {
    if (!fName.trim() || !fInstructions.trim()) return;
    setSaving(true);
    try {
      if (creating) {
        await fetch(`${BACKEND}/api/agent/templates/`, {
          method: "POST",
          headers: { "Content-Type": "application/json", ...authHeader() },
          body: JSON.stringify({ name: fName, type: fType, instructions: fInstructions, allowed_tools: fTools }),
        });
      } else if (selected?.id) {
        await fetch(`${BACKEND}/api/agent/templates/${selected.id}/`, {
          method: "PUT",
          headers: { "Content-Type": "application/json", ...authHeader() },
          body: JSON.stringify({ name: fName, type: fType, instructions: fInstructions, allowed_tools: fTools }),
        });
      }
      await fetchAgents();
      closeForm();
    } finally {
      setSaving(false);
    }
  }

  async function toggleActive(agent: AgentItem) {
    setToggling(agent.name);
    await fetch(`${BACKEND}/api/agent/templates/toggle/`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeader() },
      body: JSON.stringify({ name: agent.name, enabled: !agent.is_active }),
    });
    await fetchAgents();
    setToggling(null);
  }

  async function remove(agent: AgentItem) {
    if (!agent.id) return;
    await fetch(`${BACKEND}/api/agent/templates/${agent.id}/`, { method: "DELETE", headers: authHeader() });
    await fetchAgents();
    if (selected?.id === agent.id) closeForm();
  }

  const formOpen = userRole === "admin" && (creating || (selected !== null && !selected.builtin));

  return (
    <div className="flex flex-col h-screen bg-gray-950 text-gray-100">
      <div className="flex items-center gap-3 px-4 py-2 border-b border-gray-800 text-xs shrink-0">
        <Link href="/" className="text-gray-400 hover:text-gray-200 transition-colors font-medium">Chat</Link>
        <span className="text-gray-700">|</span>
        <Link href="/logs" className="text-gray-400 hover:text-gray-200 transition-colors font-medium">Logs</Link>
        <span className="text-gray-700">|</span>
        <span className="text-gray-300 font-medium">Agents</span>
      </div>

      <div className="flex flex-1 overflow-hidden">
        <div className="flex flex-col w-72 shrink-0 border-r border-gray-800">
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800">
            <span className="text-sm font-medium text-gray-400">Agents</span>
            {userRole === "admin" && (
              <button
                className="text-xs px-2.5 py-1 bg-blue-600 hover:bg-blue-500 rounded transition-colors"
                onClick={openCreate}
              >
                + New
              </button>
            )}
          </div>
          <div className="flex-1 overflow-y-auto py-1">
            {agents.map(agent => (
              <div
                key={agent.id ?? agent.name}
                className={`group flex items-center justify-between px-4 py-2.5 cursor-pointer hover:bg-gray-800 ${selected?.name === agent.name && !creating ? "bg-gray-800" : ""} ${!agent.is_active ? "opacity-40" : ""}`}
                onClick={() => openEdit(agent)}
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-gray-200 truncate">{agent.name}</span>
                    {agent.builtin && (
                      <span className="text-xs text-gray-500 bg-gray-700 px-1.5 py-0.5 rounded shrink-0">built-in</span>
                    )}
                  </div>
                  {agent.description && (
                    <p className="text-xs text-gray-500 truncate mt-0.5">{agent.description}</p>
                  )}
                </div>
                <div className="flex items-center gap-2 shrink-0 ml-2">
                  {userRole === "admin" && (
                    <button
                      disabled={toggling === agent.name}
                      onClick={e => { e.stopPropagation(); toggleActive(agent); }}
                      className={`relative w-8 h-4 rounded-full transition-colors duration-200 focus:outline-none disabled:opacity-50 ${agent.is_active ? "bg-blue-600" : "bg-gray-700"}`}
                    >
                      <span className={`absolute top-0.5 left-0.5 w-3 h-3 rounded-full bg-white transition-transform duration-200 ${agent.is_active ? "translate-x-4" : "translate-x-0"}`} />
                    </button>
                  )}
                  {!agent.builtin && userRole === "admin" && (
                    <button
                      className="opacity-0 group-hover:opacity-100 text-gray-600 hover:text-red-400 text-sm transition-colors"
                      onClick={e => { e.stopPropagation(); remove(agent); }}
                    >
                      ×
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {!formOpen && selected?.builtin && (
            <div className="p-6 max-w-2xl space-y-5">
              <div className="flex items-center gap-3">
                <h2 className="text-lg font-medium">{selected.name}</h2>
                <span className="text-xs text-gray-500 bg-gray-700 px-2 py-0.5 rounded">built-in</span>
              </div>
              {selected.description && <p className="text-sm text-gray-400">{selected.description}</p>}
              {selected.system_prompt && (
                <div>
                  <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">Instructions</p>
                  <textarea
                    readOnly
                    value={selected.system_prompt}
                    className="w-full bg-gray-900 border border-gray-800 rounded-lg px-3 py-2 text-xs text-gray-400 font-mono resize-none outline-none"
                    rows={10}
                  />
                </div>
              )}
              <div>
                <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">Allowed Tools</p>
                <div className="flex flex-wrap gap-2">
                  {selected.allowed_tools.map(t => (
                    <span key={t} className="text-xs bg-gray-800 text-gray-300 px-2 py-1 rounded">{toolLabel(t)}</span>
                  ))}
                </div>
              </div>
              <p className="text-xs text-gray-600">Built-in agents cannot be edited. Create a custom agent with the same name to override.</p>
            </div>
          )}

          {formOpen && (
            <div className="p-6 max-w-2xl">
              <h2 className="text-lg font-medium mb-5">{creating ? "New Agent" : `Edit — ${selected?.name}`}</h2>

              <div className="space-y-4">
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Name</label>
                  <input
                    className="w-full bg-gray-800 rounded-lg px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-blue-600"
                    value={fName}
                    onChange={e => setFName(e.target.value)}
                    placeholder="e.g. reconciliation_agent"
                  />
                </div>

                <div>
                  <label className="block text-xs text-gray-400 mb-1">Role</label>
                  <input
                    className="w-full bg-gray-800 rounded-lg px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-blue-600"
                    value={fType}
                    onChange={e => setFType(e.target.value)}
                    placeholder="e.g. Procurement, Analytics, HR..."
                  />
                </div>

                <div>
                  <label className="block text-xs text-gray-400 mb-1">Instructions</label>
                  <textarea
                    className="w-full bg-gray-800 rounded-lg px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-blue-600 resize-none font-mono"
                    rows={8}
                    value={fInstructions}
                    onChange={e => setFInstructions(e.target.value)}
                    placeholder="Describe the agent's role, behavior, and focus area..."
                  />
                </div>

                <div>
                  <label className="block text-xs text-gray-400 mb-2">Allowed Tools</label>
                  <div className="space-y-1.5">
                    {tools.map(tool => (
                      <label key={tool} className="flex items-center gap-2.5 cursor-pointer group">
                        <input
                          type="checkbox"
                          checked={fTools.includes(tool)}
                          onChange={() => toggleTool(tool)}
                          className="accent-blue-500"
                        />
                        <span className="text-sm text-gray-300 group-hover:text-gray-100 transition-colors">{toolLabel(tool)}</span>
                        <span className="text-xs text-gray-600 font-mono">{tool}</span>
                      </label>
                    ))}
                  </div>
                </div>

                <div className="flex gap-2 pt-2">
                  <button
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-sm font-medium disabled:opacity-40 transition-colors"
                    onClick={save}
                    disabled={saving || !fName.trim() || !fInstructions.trim()}
                  >
                    {saving ? "Saving..." : "Save"}
                  </button>
                  <button
                    className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm transition-colors"
                    onClick={closeForm}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          )}

          {!formOpen && !selected && (
            <div className="flex items-center justify-center h-full text-sm text-gray-600">
              Select an agent to view or click + New to create one.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
