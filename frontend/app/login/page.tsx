"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { BACKEND } from "../lib/api";

const DEMO_USERS = [
  { label: "Admin", username: "admin", password: "admin" },
  { label: "Operator", username: "operator", password: "operator" },
  { label: "Viewer", username: "viewer", password: "viewer" },
];

export default function LoginPage() {
  const router = useRouter();

  useEffect(() => {
    if (localStorage.getItem("access_token")) router.replace("/");
  }, [router]);

  async function login(username: string, password: string) {
    try {
      const res = await fetch(`${BACKEND}/api/users/login/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      if (!res.ok) return;
      const data = await res.json();
      localStorage.setItem("access_token", data.access);
      localStorage.setItem("user_role", data.role);
      localStorage.setItem("username", username);
      router.push("/");
    } catch {}
  }

  return (
    <div className="flex items-center justify-center h-screen bg-gray-950 text-gray-100">
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-8 w-80 space-y-5">
        <div>
          <h1 className="text-lg font-medium">Sign in</h1>
          <p className="text-xs text-gray-500 mt-1">Select a user to continue</p>
        </div>
        <div className="space-y-2">
          {DEMO_USERS.map(u => (
            <button
              key={u.username}
              className="w-full px-4 py-2.5 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm text-left flex items-center justify-between transition-colors"
              onClick={() => login(u.username, u.password)}
            >
              <span className="font-medium">{u.label}</span>
              <span className="text-xs text-gray-500">{u.username}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
