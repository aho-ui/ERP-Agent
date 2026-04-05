"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

const NAV_ALL = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/", label: "Chat" },
];

const NAV_OPERATOR = [
  { href: "/logs", label: "Logs" },
];

const NAV_ADMIN = [
  { href: "/agents", label: "Agents" },
  { href: "/bots", label: "Bots" },
  { href: "/users", label: "Users" },
];

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const [role, setRole] = useState("");

  useEffect(() => {
    setRole(localStorage.getItem("user_role") ?? "");
  }, [pathname]);

  if (pathname === "/login") return null;

  function logout() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("user_role");
    localStorage.removeItem("username");
    router.push("/login");
  }

  return (
    <div className="w-52 shrink-0 flex flex-col bg-gray-900 border-r border-gray-800">
      <div className="px-4 py-4 border-b border-gray-800">
        <span className="text-sm font-semibold text-gray-100">Nanobot</span>
      </div>

      <nav className="flex-1 px-2 py-3 space-y-0.5">
        {NAV_ALL.map(({ href, label }) => (
          <Link
            key={href}
            href={href}
            className={`flex items-center px-3 py-2 rounded-lg text-sm transition-colors ${
              pathname === href
                ? "bg-gray-800 text-gray-100"
                : "text-gray-400 hover:text-gray-200 hover:bg-gray-800/50"
            }`}
          >
            {label}
          </Link>
        ))}

        {(role === "operator" || role === "admin") && (
          <>
            <div className="pt-3 pb-1 px-3">
              <span className="text-[10px] font-medium text-gray-600 uppercase tracking-wider">Workspace</span>
            </div>
            {NAV_OPERATOR.map(({ href, label }) => (
              <Link
                key={href}
                href={href}
                className={`flex items-center px-3 py-2 rounded-lg text-sm transition-colors ${
                  pathname === href
                    ? "bg-gray-800 text-gray-100"
                    : "text-gray-400 hover:text-gray-200 hover:bg-gray-800/50"
                }`}
              >
                {label}
              </Link>
            ))}
          </>
        )}

        {role === "admin" && (
          <>
            <div className="pt-3 pb-1 px-3">
              <span className="text-[10px] font-medium text-gray-600 uppercase tracking-wider">Admin</span>
            </div>
            {NAV_ADMIN.map(({ href, label }) => (
              <Link
                key={href}
                href={href}
                className={`flex items-center px-3 py-2 rounded-lg text-sm transition-colors ${
                  pathname === href
                    ? "bg-gray-800 text-gray-100"
                    : "text-gray-400 hover:text-gray-200 hover:bg-gray-800/50"
                }`}
              >
                {label}
              </Link>
            ))}
          </>
        )}
      </nav>

      <div className="px-2 py-3 border-t border-gray-800">
        <button
          onClick={logout}
          className="w-full flex items-center px-3 py-2 rounded-lg text-sm text-gray-500 hover:text-gray-300 hover:bg-gray-800/50 transition-colors"
        >
          Sign out
        </button>
      </div>
    </div>
  );
}
