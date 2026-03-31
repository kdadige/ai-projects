// lib/api.ts - Backend API client

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface TokenResponse {
  access_token: string;
  token_type: string;
  username: string;
  full_name: string;
  role: string;
  department: string;
  accessible_collections: string[];
}

export interface ChatRequest {
  question: string;
  top_k?: number;
}

export interface CitationInfo {
  source_document: string;
  page_number: number;
  section_title: string;
  collection: string;
  score: number;
}

export interface GuardrailWarning {
  type: string;
  message: string;
}

export interface RetrievedChunk {
  text: string;
  source_document: string;
  page_number: number;
  section_title: string;
  score: number;
}

export interface ChatResponse {
  answer: string;
  route: string;
  target_collections: string[];
  user_role: string;
  accessible_collections: string[];
  retrieved_chunks: RetrievedChunk[];
  input_guardrail_triggered: boolean;
  output_guardrail_triggered: boolean;
  guardrail_warnings: GuardrailWarning[];
  citations: CitationInfo[];
  session_query_count: number;
}

export interface UserRecord {
  username: string;
  full_name: string;
  role: string;
  department: string;
  accessible_collections: string[];
}

export interface DocumentRecord {
  source_document: string;
  collection: string;
  access_roles: string[];
}

export interface CollectionStats {
  total_points: number;
  collection_name: string;
  status: string;
}

class ApiClient {
  private token: string | null = null;

  setToken(token: string) {
    this.token = token;
    if (typeof window !== "undefined") {
      localStorage.setItem("finbot_token", token);
    }
  }

  getToken(): string | null {
    if (this.token) return this.token;
    if (typeof window !== "undefined") {
      this.token = localStorage.getItem("finbot_token");
    }
    return this.token;
  }

  clearToken() {
    this.token = null;
    if (typeof window !== "undefined") {
      localStorage.removeItem("finbot_token");
      localStorage.removeItem("finbot_user");
    }
  }

  private async request<T>(
    path: string,
    options: RequestInit = {}
  ): Promise<T> {
    const token = this.getToken();
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string>),
    };
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const res = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }

    if (res.status === 204) return {} as T;
    return res.json();
  }

  async login(username: string, password: string): Promise<TokenResponse> {
    const data = await this.request<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
    this.setToken(data.access_token);
    if (typeof window !== "undefined") {
      localStorage.setItem("finbot_user", JSON.stringify(data));
    }
    return data;
  }

  async getMe(): Promise<UserRecord> {
    return this.request<UserRecord>("/auth/me");
  }

  async chat(question: string, top_k = 5): Promise<ChatResponse> {
    return this.request<ChatResponse>("/chat", {
      method: "POST",
      body: JSON.stringify({ question, top_k }),
    });
  }

  // Admin
  async getUsers(): Promise<UserRecord[]> {
    return this.request<UserRecord[]>("/admin/users");
  }

  async createUser(data: {
    username: string;
    full_name: string;
    role: string;
    department: string;
    password: string;
  }): Promise<UserRecord> {
    return this.request<UserRecord>("/admin/users", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async updateUser(
    username: string,
    data: Partial<{ full_name: string; role: string; department: string; password: string }>
  ): Promise<UserRecord> {
    return this.request<UserRecord>(`/admin/users/${username}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  }

  async deleteUser(username: string): Promise<void> {
    return this.request<void>(`/admin/users/${username}`, { method: "DELETE" });
  }

  async getDocuments(): Promise<DocumentRecord[]> {
    return this.request<DocumentRecord[]>("/admin/documents");
  }

  async uploadDocument(file: File, collection: string): Promise<unknown> {
    const token = this.getToken();
    const formData = new FormData();
    formData.append("file", file);
    formData.append("collection", collection);

    const res = await fetch(`${API_BASE}/admin/documents/upload`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.json();
  }

  async deleteDocument(sourceDocument: string): Promise<void> {
    return this.request<void>(
      `/admin/documents/${encodeURIComponent(sourceDocument)}`,
      { method: "DELETE" }
    );
  }

  async getStats(): Promise<CollectionStats> {
    return this.request<CollectionStats>("/admin/stats");
  }
}

export const api = new ApiClient();

