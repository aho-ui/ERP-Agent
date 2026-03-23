"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

const BACKEND = "http://localhost:8000";

const ROLES = ["viewer", "operator", "admin"];

const ROLE_STYLES: Record<string, string> = {
  admin: "bg-purple-900/50 text-purple-300",
  operator: "bg-blue-900/50 text-blue-300",
  viewer: "bg-gray-800 text-gray-400",
};

type UserRow = {
  id: string;
  username: string;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string;
};

type FormState = { username: string; email: string; password: string; role: string };

const emptyForm: FormState = { username: "", email: "", password: "", role: "viewer" };

export default function UsersPage() {
  const router = useRouter();
  const [users, setUsers] = useState<UserRow[]>([]);
  const [formOpen, setFormOpen] = useState(false);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [formError, setFormError] = useState("");
  const [saving, setSaving] = useState(false);

  function token() {
    return localStorage.getItem("access_token") ?? "";
  }

  function authHeaders() {
    return { "Content-Type": "application/json", Authorization: `Bearer ${token()}` };
  }

  async function fetchUsers() {
    const res = await fetch(`${BACKEND}/api/users/`, { headers: authHeaders() });
    if (res.status === 401 || res.status === 403) { router.replace("/"); return; }
    setUsers(await res.json());
  }

  useEffect(() => {
    if (!localStorage.getItem("access_token")) { router.replace("/login"); return; }
    if (localStorage.getItem("user_role") !== "admin") { router.replace("/"); return; }
    fetchUsers();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function createUser() {
    if (!form.username || !form.password) { setFormError("Username and password are required."); return; }
    setSaving(true);
    setFormError("");
    const res = await fetch(`${BACKEND}/api/users/`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify(form),
    });
    setSaving(false);
    if (!res.ok) {
      const data = await res.json();
      setFormError(data.error ?? "Failed to create user.");
      return;
    }
    setForm(emptyForm);
    setFormOpen(false);
    fetchUsers();
  }

  async function updateUser(id: string, patch: Partial<UserRow>) {
    await fetch(`${BACKEND}/api/users/${id}/`, {
      method: "PUT",
      headers: authHeaders(),
      body: JSON.stringify(patch),
    });
    fetchUsers();
  }

  async function deleteUser(id: string) {
    await fetch(`${BACKEND}/api/users/${id}/`, { method: "DELETE", headers: authHeaders() });
    fetchUsers();
  }

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <div className="flex items-center gap-4 px-6 py-3 border-b border-gray-800 text-sm">
        <Link href="/" className="text-gray-400 hover:text-gray-200 transition-colors">Chat</Link>
        <span className="text-gray-600">/</span>
        <span className="text-gray-200">Users</span>
        <div className="ml-auto">
          <button
            onClick={() => { setFormOpen(true); setForm(emptyForm); setFormError(""); }}
            className="text-xs bg-indigo-600 hover:bg-indigo-500 text-white px-3 py-1.5 rounded transition-colors"
          >
            + New User
          </button>
        </div>
      </div>

      {formOpen && (
        <div className="px-6 py-4 border-b border-gray-800 bg-gray-900/50">
          <div className="max-w-lg space-y-3">
            <p className="text-xs text-gray-400 font-medium uppercase tracking-wide">New User</p>
            {formError && <p className="text-xs text-red-400">{formError}</p>}
            <div className="grid grid-cols-2 gap-3">
              <input
                placeholder="Username"
                value={form.username}
                onChange={(e) => setForm({ ...form, username: e.target.value })}
                className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-gray-100 placeholder-gray-600 focus:outline-none focus:border-indigo-500"
              />
              <input
                placeholder="Email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-gray-100 placeholder-gray-600 focus:outline-none focus:border-indigo-500"
              />
              <input
                placeholder="Password"
                type="password"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-gray-100 placeholder-gray-600 focus:outline-none focus:border-indigo-500"
              />
              <select
                value={form.role}
                onChange={(e) => setForm({ ...form, role: e.target.value })}
                className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-indigo-500"
              >
                {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
            </div>
            <div className="flex gap-2">
              <button
                onClick={createUser}
                disabled={saving}
                className="text-xs bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white px-4 py-1.5 rounded transition-colors"
              >
                {saving ? "Creating..." : "Create"}
              </button>
              <button
                onClick={() => setFormOpen(false)}
                className="text-xs text-gray-400 hover:text-gray-200 px-4 py-1.5 rounded transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="px-6 py-6">
        <div className="rounded-lg border border-gray-800 overflow-hidden">
          <table className="w-full text-sm text-left">
            <thead className="bg-gray-800 text-gray-400 text-xs uppercase">
              <tr>
                <th className="px-4 py-3 font-medium">Username</th>
                <th className="px-4 py-3 font-medium">Email</th>
                <th className="px-4 py-3 font-medium">Role</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Created</th>
                <th className="px-4 py-3 font-medium"></th>
              </tr>
            </thead>
            <tbody>
              {users.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-6 text-center text-gray-600 text-xs">No users found.</td>
                </tr>
              )}
              {users.map((u) => (
                <tr key={u.id} className="border-t border-gray-800 hover:bg-gray-900/40">
                  <td className="px-4 py-3 text-xs text-gray-200 font-mono">{u.username}</td>
                  <td className="px-4 py-3 text-xs text-gray-400">{u.email || "—"}</td>
                  <td className="px-4 py-3">
                    <select
                      value={u.role}
                      onChange={(e) => updateUser(u.id, { role: e.target.value })}
                      className={`text-xs px-2 py-1 rounded border-0 focus:outline-none focus:ring-1 focus:ring-indigo-500 ${ROLE_STYLES[u.role] ?? "bg-gray-800 text-gray-400"}`}
                    >
                      {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                    </select>
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => updateUser(u.id, { is_active: !u.is_active })}
                      className={`text-xs px-2 py-1 rounded transition-colors ${u.is_active ? "text-green-400 hover:text-red-400" : "text-red-400 hover:text-green-400"}`}
                    >
                      {u.is_active ? "Active" : "Inactive"}
                    </button>
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500 font-mono whitespace-nowrap">
                    {new Date(u.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => deleteUser(u.id)}
                      className="text-xs text-gray-600 hover:text-red-400 transition-colors"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
