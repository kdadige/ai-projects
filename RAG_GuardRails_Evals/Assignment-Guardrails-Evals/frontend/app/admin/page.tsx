"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, UserRecord, DocumentRecord, CollectionStats, TokenResponse } from "@/lib/api";

const ROLES = ["employee", "finance", "engineering", "marketing", "c_level"];
const COLLECTIONS = ["general", "finance", "engineering", "marketing", "hr"];

export default function AdminPage() {
  const router = useRouter();
  const [user, setUser] = useState<TokenResponse | null>(null);
  const [users, setUsers] = useState<UserRecord[]>([]);
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [stats, setStats] = useState<CollectionStats | null>(null);
  const [activeTab, setActiveTab] = useState<"users" | "documents" | "stats">("users");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // Create user form
  const [newUser, setNewUser] = useState({ username: "", full_name: "", role: "employee", department: "", password: "" });
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadCollection, setUploadCollection] = useState("general");

  useEffect(() => {
    const stored = localStorage.getItem("finbot_user");
    if (!stored) { router.push("/login"); return; }
    const u = JSON.parse(stored) as TokenResponse;
    setUser(u);
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [u, d, s] = await Promise.all([api.getUsers(), api.getDocuments(), api.getStats()]);
      setUsers(u);
      setDocuments(d);
      setStats(s);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  };

  const handleCreateUser = async () => {
    if (!newUser.username || !newUser.full_name || !newUser.password || !newUser.department) {
      setError("All fields are required"); return;
    }
    setLoading(true); setError(""); setSuccess("");
    try {
      await api.createUser(newUser);
      setSuccess(`User ${newUser.username} created`);
      setNewUser({ username: "", full_name: "", role: "employee", department: "", password: "" });
      await loadData();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create user");
    } finally { setLoading(false); }
  };

  const handleDeleteUser = async (username: string) => {
    if (!confirm(`Delete user ${username}?`)) return;
    setLoading(true); setError(""); setSuccess("");
    try {
      await api.deleteUser(username);
      setSuccess(`User ${username} deleted`);
      await loadData();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to delete user");
    } finally { setLoading(false); }
  };

  const handleUploadDocument = async () => {
    if (!uploadFile) { setError("Please select a file"); return; }
    setLoading(true); setError(""); setSuccess("");
    try {
      const result = await api.uploadDocument(uploadFile, uploadCollection) as { chunks_created: number };
      setSuccess(`Uploaded ${uploadFile.name}: ${result.chunks_created} chunks indexed`);
      setUploadFile(null);
      await loadData();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally { setLoading(false); }
  };

  const handleDeleteDocument = async (doc: string) => {
    if (!confirm(`Remove ${doc} from the index?`)) return;
    setLoading(true); setError(""); setSuccess("");
    try {
      await api.deleteDocument(doc);
      setSuccess(`Document ${doc} removed`);
      await loadData();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to delete document");
    } finally { setLoading(false); }
  };

  if (!user) return null;

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <div className="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button onClick={() => router.push("/chat")} className="text-slate-500 hover:text-slate-700">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <div>
            <h1 className="text-xl font-bold text-slate-800">Admin Panel</h1>
            <p className="text-slate-500 text-sm">Manage users and documents</p>
          </div>
        </div>
        <div className="text-sm text-slate-500">Logged in as <strong>{user.username}</strong></div>
      </div>

      <div className="max-w-6xl mx-auto p-6">
        {/* Alerts */}
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm flex justify-between">
            {error}
            <button onClick={() => setError("")} className="ml-2 text-red-400 hover:text-red-600">✕</button>
          </div>
        )}
        {success && (
          <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg text-green-700 text-sm flex justify-between">
            {success}
            <button onClick={() => setSuccess("")} className="ml-2 text-green-400 hover:text-green-600">✕</button>
          </div>
        )}

        {/* Stats Bar */}
        {stats && (
          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="bg-white rounded-xl border border-slate-200 p-4">
              <p className="text-slate-500 text-sm">Total Chunks Indexed</p>
              <p className="text-3xl font-bold text-slate-800">{stats.total_points.toLocaleString()}</p>
            </div>
            <div className="bg-white rounded-xl border border-slate-200 p-4">
              <p className="text-slate-500 text-sm">Documents</p>
              <p className="text-3xl font-bold text-slate-800">{documents.length}</p>
            </div>
            <div className="bg-white rounded-xl border border-slate-200 p-4">
              <p className="text-slate-500 text-sm">Users</p>
              <p className="text-3xl font-bold text-slate-800">{users.length}</p>
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-2 mb-6">
          {(["users", "documents"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors capitalize ${
                activeTab === tab ? "bg-blue-600 text-white" : "bg-white border border-slate-200 text-slate-600 hover:border-slate-300"
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Users Tab */}
        {activeTab === "users" && (
          <div className="grid grid-cols-3 gap-6">
            {/* User list */}
            <div className="col-span-2 bg-white rounded-xl border border-slate-200 overflow-hidden">
              <div className="px-4 py-3 border-b border-slate-200 font-medium text-slate-700">All Users</div>
              <div className="divide-y divide-slate-100">
                {users.map((u) => (
                  <div key={u.username} className="px-4 py-3 flex items-center justify-between hover:bg-slate-50">
                    <div>
                      <p className="font-medium text-sm text-slate-800">{u.full_name}</p>
                      <p className="text-xs text-slate-500">{u.username} · {u.department}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full">{u.role}</span>
                      <span className="text-xs text-slate-400">{u.accessible_collections.join(", ")}</span>
                      <button
                        onClick={() => handleDeleteUser(u.username)}
                        className="text-red-400 hover:text-red-600 text-xs"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Create user form */}
            <div className="bg-white rounded-xl border border-slate-200 p-4">
              <h3 className="font-medium text-slate-700 mb-4">Add New User</h3>
              <div className="space-y-3">
                {[
                  { key: "username", label: "Username", placeholder: "john_doe" },
                  { key: "full_name", label: "Full Name", placeholder: "John Doe" },
                  { key: "department", label: "Department", placeholder: "Finance" },
                  { key: "password", label: "Password", placeholder: "••••••••" },
                ].map(({ key, label, placeholder }) => (
                  <div key={key}>
                    <label className="block text-xs font-medium text-slate-600 mb-1">{label}</label>
                    <input
                      type={key === "password" ? "password" : "text"}
                      value={newUser[key as keyof typeof newUser]}
                      onChange={(e) => setNewUser({ ...newUser, [key]: e.target.value })}
                      placeholder={placeholder}
                      className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                    />
                  </div>
                ))}
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Role</label>
                  <select
                    value={newUser.role}
                    onChange={(e) => setNewUser({ ...newUser, role: e.target.value })}
                    className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                  >
                    {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                  </select>
                </div>
                <button
                  onClick={handleCreateUser}
                  disabled={loading}
                  className="w-full py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white rounded-lg text-sm font-medium"
                >
                  Create User
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Documents Tab */}
        {activeTab === "documents" && (
          <div className="grid grid-cols-3 gap-6">
            {/* Document list */}
            <div className="col-span-2 bg-white rounded-xl border border-slate-200 overflow-hidden">
              <div className="px-4 py-3 border-b border-slate-200 font-medium text-slate-700">Indexed Documents</div>
              <div className="divide-y divide-slate-100">
                {documents.length === 0 && (
                  <p className="px-4 py-6 text-center text-slate-400 text-sm">No documents indexed yet. Run the ingestion script or upload a document.</p>
                )}
                {documents.map((d) => (
                  <div key={d.source_document} className="px-4 py-3 flex items-center justify-between hover:bg-slate-50">
                    <div>
                      <p className="font-medium text-sm text-slate-800">{d.source_document}</p>
                      <p className="text-xs text-slate-500">Collection: {d.collection} · Access: {d.access_roles.join(", ")}</p>
                    </div>
                    <button
                      onClick={() => handleDeleteDocument(d.source_document)}
                      className="text-red-400 hover:text-red-600 text-xs"
                    >
                      Remove
                    </button>
                  </div>
                ))}
              </div>
            </div>

            {/* Upload form */}
            <div className="bg-white rounded-xl border border-slate-200 p-4">
              <h3 className="font-medium text-slate-700 mb-4">Upload Document</h3>
              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Collection</label>
                  <select
                    value={uploadCollection}
                    onChange={(e) => setUploadCollection(e.target.value)}
                    className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                  >
                    {COLLECTIONS.map((c) => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">File</label>
                  <input
                    type="file"
                    accept=".pdf,.docx,.md,.csv,.txt"
                    onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                    className="w-full text-sm text-slate-600 file:mr-3 file:py-1.5 file:px-3 file:rounded file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                  />
                  <p className="text-xs text-slate-400 mt-1">PDF, DOCX, MD, CSV, TXT</p>
                </div>
                <button
                  onClick={handleUploadDocument}
                  disabled={loading || !uploadFile}
                  className="w-full py-2 bg-green-600 hover:bg-green-700 disabled:bg-green-300 text-white rounded-lg text-sm font-medium"
                >
                  {loading ? "Uploading..." : "Upload & Index"}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

