"use client";
import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { api, ChatResponse, TokenResponse } from "@/lib/api";

const ROUTE_COLORS: Record<string, string> = {
  finance_route: "bg-green-100 text-green-800",
  engineering_route: "bg-blue-100 text-blue-800",
  marketing_route: "bg-purple-100 text-purple-800",
  hr_general_route: "bg-yellow-100 text-yellow-800",
  cross_department_route: "bg-orange-100 text-orange-800",
  blocked: "bg-red-100 text-red-800",
};

const ROLE_COLORS: Record<string, string> = {
  employee: "bg-gray-100 text-gray-700",
  finance: "bg-green-100 text-green-700",
  engineering: "bg-blue-100 text-blue-700",
  marketing: "bg-purple-100 text-purple-700",
  c_level: "bg-red-100 text-red-700",
};

const COLLECTION_ICONS: Record<string, string> = {
  general: "📋",
  finance: "💰",
  engineering: "⚙️",
  marketing: "📢",
  hr: "👥",
};

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  response?: ChatResponse;
  timestamp: Date;
}

export default function ChatPage() {
  const router = useRouter();
  const [user, setUser] = useState<TokenResponse | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [showChunks, setShowChunks] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const stored = localStorage.getItem("finbot_user");
    if (!stored) {
      router.push("/login");
      return;
    }
    setUser(JSON.parse(stored));
  }, [router]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;
    const question = input.trim();
    setInput("");

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: question,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const response = await api.chat(question);
      const assistantMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: response.answer,
        response,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (e: unknown) {
      const errMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: `Error: ${e instanceof Error ? e.message : "Something went wrong"}`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errMsg]);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    api.clearToken();
    router.push("/login");
  };

  if (!user) return null;

  return (
    <div className="flex h-screen bg-slate-50">
      {/* Sidebar */}
      <div className="w-72 bg-slate-900 text-white flex flex-col p-4">
        <div className="mb-6">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 bg-blue-600 rounded-full flex items-center justify-center font-bold text-lg">
              {user.full_name[0]}
            </div>
            <div>
              <p className="font-semibold text-sm">{user.full_name}</p>
              <p className="text-slate-400 text-xs">{user.department}</p>
            </div>
          </div>
          <div className={`inline-flex px-2 py-1 rounded text-xs font-medium mt-1 ${ROLE_COLORS[user.role] || "bg-gray-100 text-gray-700"}`}>
            Role: {user.role}
          </div>
        </div>

        <div className="mb-6">
          <p className="text-slate-400 text-xs uppercase tracking-wider mb-2">My Access</p>
          <div className="space-y-1">
            {user.accessible_collections.map((col) => (
              <div key={col} className="flex items-center gap-2 text-sm text-slate-300">
                <span>{COLLECTION_ICONS[col] || "📄"}</span>
                <span className="capitalize">{col}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-auto space-y-2">
          <button
            onClick={() => router.push("/admin")}
            className="w-full py-2 px-3 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm transition-colors flex items-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            Admin Panel
          </button>
          <button
            onClick={handleLogout}
            className="w-full py-2 px-3 bg-red-700 hover:bg-red-600 rounded-lg text-sm transition-colors"
          >
            Sign Out
          </button>
        </div>
      </div>

      {/* Main Chat */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-slate-800">FinBot</h1>
            <p className="text-slate-500 text-sm">Ask anything about FinSolve's knowledge base</p>
          </div>
          <div className="flex items-center gap-2">
            {messages.length > 0 && (
              <button
                onClick={() => setMessages([])}
                className="text-sm text-slate-500 hover:text-slate-700 px-3 py-1 rounded border border-slate-200 hover:border-slate-300 transition-colors"
              >
                Clear
              </button>
            )}
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.length === 0 && (
            <div className="text-center py-16 text-slate-400">
              <div className="text-5xl mb-4">💬</div>
              <p className="text-lg font-medium">Start a conversation</p>
              <p className="text-sm mt-1">Ask questions about company policies, reports, or documentation</p>
              <div className="mt-6 grid grid-cols-2 gap-3 max-w-lg mx-auto">
                {["What is the leave policy?", "How did the Q3 campaign perform?", "What are the system SLA requirements?", "Show me the Q3 financial report"].map((q) => (
                  <button
                    key={q}
                    onClick={() => { setInput(q); }}
                    className="text-left p-3 bg-white border border-slate-200 rounded-lg text-sm text-slate-600 hover:border-blue-300 hover:text-blue-600 transition-colors"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg) => (
            <div key={msg.id} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-3xl ${msg.role === "user" ? "w-auto" : "w-full"}`}>
                {msg.role === "user" ? (
                  <div className="bg-blue-600 text-white rounded-2xl rounded-tr-sm px-4 py-3 text-sm">
                    {msg.content}
                  </div>
                ) : (
                  <div className="bg-white rounded-2xl rounded-tl-sm border border-slate-200 overflow-hidden shadow-sm">
                    {/* Guardrail Warning Banner */}
                    {msg.response && (msg.response.input_guardrail_triggered || msg.response.output_guardrail_triggered) && (
                      <div className="bg-amber-50 border-b border-amber-200 px-4 py-2 flex items-start gap-2">
                        <span className="text-amber-500 mt-0.5">⚠️</span>
                        <div>
                          <p className="text-amber-800 text-xs font-semibold">Guardrail Triggered</p>
                          {msg.response.guardrail_warnings.map((w, i) => (
                            <p key={i} className="text-amber-700 text-xs mt-0.5">{w.message}</p>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Answer */}
                    <div className="px-4 py-3">
                      <p className="text-slate-800 text-sm whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                    </div>

                    {/* Metadata row */}
                    {msg.response && (
                      <div className="px-4 py-2 bg-slate-50 border-t border-slate-100 flex flex-wrap gap-2 items-center">
                        {/* Route badge */}
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${ROUTE_COLORS[msg.response.route] || "bg-slate-100 text-slate-600"}`}>
                          🔀 {msg.response.route.replace("_route", "").replace("_", " ")}
                        </span>

                        {/* Collections searched */}
                        {msg.response.target_collections.map((c) => (
                          <span key={c} className="inline-flex items-center gap-1 px-2 py-0.5 bg-slate-100 text-slate-600 rounded-full text-xs">
                            {COLLECTION_ICONS[c] || "📄"} {c}
                          </span>
                        ))}

                        {/* Citations */}
                        {msg.response.citations.length > 0 && (
                          <button
                            onClick={() => setShowChunks(showChunks === msg.id ? null : msg.id)}
                            className="ml-auto text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1"
                          >
                            📎 {msg.response.citations.length} source{msg.response.citations.length !== 1 ? "s" : ""}
                          </button>
                        )}
                      </div>
                    )}

                    {/* Citations panel */}
                    {msg.response && showChunks === msg.id && (
                      <div className="px-4 py-3 bg-slate-50 border-t border-slate-200 space-y-2">
                        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Sources</p>
                        {msg.response.citations.map((c, i) => (
                          <div key={i} className="flex items-start gap-2 text-xs text-slate-600">
                            <span className="mt-0.5 text-slate-400">•</span>
                            <div>
                              <span className="font-medium">{c.source_document}</span>
                              <span className="text-slate-400"> · p.{c.page_number}</span>
                              {c.section_title && <span className="text-slate-400"> · {c.section_title}</span>}
                              <span className="ml-1 px-1 py-0.5 bg-white border border-slate-200 rounded text-xs">{COLLECTION_ICONS[c.collection]} {c.collection}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
                <p className="text-xs text-slate-400 mt-1 px-1">
                  {msg.timestamp.toLocaleTimeString()}
                </p>
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex justify-start">
              <div className="bg-white border border-slate-200 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm">
                <div className="flex gap-1">
                  <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                  <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                  <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                </div>
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="bg-white border-t border-slate-200 p-4">
          <div className="flex gap-3 max-w-4xl mx-auto">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
              placeholder="Ask a question about FinSolve's documents..."
              className="flex-1 px-4 py-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none text-sm"
            />
            <button
              onClick={handleSend}
              disabled={loading || !input.trim()}
              className="px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white rounded-xl font-medium transition-colors flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
              Send
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

