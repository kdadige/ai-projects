"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, TokenResponse } from "@/lib/api";

const DEMO_USERS = [
  { username: "alice_employee", password: "employee123", role: "Employee", color: "bg-gray-500" },
  { username: "bob_finance", password: "finance123", role: "Finance", color: "bg-green-600" },
  { username: "carol_engineering", password: "engineering123", role: "Engineering", color: "bg-blue-600" },
  { username: "dave_marketing", password: "marketing123", role: "Marketing", color: "bg-purple-600" },
  { username: "eve_clevel", password: "clevel123", role: "C-Level", color: "bg-red-600" },
];

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleLogin = async (u: string, p: string) => {
    setLoading(true);
    setError("");
    try {
      const data: TokenResponse = await api.login(u, p);
      localStorage.setItem("finbot_user", JSON.stringify(data));
      router.push("/chat");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-700 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-8">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-600 rounded-full mb-4">
            <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.347.347a3.75 3.75 0 01-5.303 0l-.347-.347z" />
            </svg>
          </div>
          <h1 className="text-3xl font-bold text-slate-800">FinBot</h1>
          <p className="text-slate-500 mt-1">FinSolve Technologies Internal Assistant</p>
        </div>

        {/* Manual Login */}
        <div className="space-y-4 mb-6">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
              placeholder="Enter username"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleLogin(username, password)}
              className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
              placeholder="Enter password"
            />
          </div>
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              {error}
            </div>
          )}
          <button
            onClick={() => handleLogin(username, password)}
            disabled={loading || !username || !password}
            className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white font-semibold rounded-lg transition-colors"
          >
            {loading ? "Signing in..." : "Sign In"}
          </button>
        </div>

        {/* Divider */}
        <div className="relative mb-6">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-slate-200" />
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="px-2 bg-white text-slate-400">or use a demo account</span>
          </div>
        </div>

        {/* Demo User Buttons */}
        <div className="space-y-2">
          {DEMO_USERS.map((u) => (
            <button
              key={u.username}
              onClick={() => handleLogin(u.username, u.password)}
              disabled={loading}
              className={`w-full flex items-center justify-between px-4 py-3 ${u.color} text-white rounded-lg hover:opacity-90 disabled:opacity-50 transition-opacity`}
            >
              <div className="text-left">
                <div className="font-semibold text-sm">{u.username}</div>
                <div className="text-xs opacity-80">Role: {u.role}</div>
              </div>
              <svg className="w-4 h-4 opacity-70" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
          ))}
        </div>

        <p className="text-center text-xs text-slate-400 mt-6">
          Admin: <code className="bg-slate-100 px-1 rounded">admin</code> / <code className="bg-slate-100 px-1 rounded">admin123</code>
        </p>
      </div>
    </div>
  );
}

