"use client";

import { useRouter } from "next/navigation";

export const BACKEND = "http://localhost:8000";

export function useApi() {
  const router = useRouter();

  function authHeader(): Record<string, string> {
    return { "Authorization": `Bearer ${localStorage.getItem("access_token") ?? ""}` };
  }

  async function apiFetch<T = unknown>(url: string, init?: RequestInit): Promise<T | null> {
    const res = await fetch(url, {
      ...init,
      headers: { ...authHeader(), ...(init?.headers as Record<string, string> ?? {}) },
    });
    if (res.status === 401) { localStorage.removeItem("access_token"); router.replace("/login"); return null; }
    return res.ok ? res.json() : null;
  }

  return { apiFetch, authHeader };
}
