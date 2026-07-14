const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:4000/api";

interface FetchOptions extends RequestInit {
  useToken?: boolean;
}

async function apiRequest(path: string, options: FetchOptions = {}) {
  const { useToken = true, ...init } = options;
  const headers = new Headers(init.headers || {});
  
  // Inject JWT access token if user is authenticated
  if (useToken && typeof window !== "undefined") {
    const token = localStorage.getItem("token");
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }
  }
  
  // Inject active model preference header if set in localStorage
  if (typeof window !== "undefined") {
    const activeModel = localStorage.getItem("activeModel");
    if (activeModel) {
      headers.set("X-Ollama-Model", activeModel);
    }
  }
  
  // Set JSON headers ONLY if body is NOT FormData (multipart/form-data boundary is managed by the browser)
  if (!(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers
    });
    
    if (!response.ok) {
      let errorMessage = "Server transaction failed.";
      try {
        const errData = await response.json();
        if (errData.detail) {
          if (typeof errData.detail === "string") {
            errorMessage = errData.detail;
          } else if (Array.isArray(errData.detail)) {
            // Check for validation structure e.g. [{"msg": "..."}]
            errorMessage = errData.detail[0]?.msg || JSON.stringify(errData.detail);
          } else {
            errorMessage = JSON.stringify(errData.detail);
          }
        }
      } catch {
        // Fallback to text if JSON parse fails
        const text = await response.text();
        if (text) errorMessage = text;
      }
      throw new Error(errorMessage);
    }
    
    return await response.json();
  } catch (error: any) {
    // Forward standard errors
    throw new Error(error.message || "Network connection failed. Please ensure the backend is running.");
  }
}

// CENTRALIZED API EXPORTS
export const api = {
  // 1. Authentication
  async register(name: string, email: string, password: string) {
    return apiRequest("/auth/register", {
      method: "POST",
      useToken: false,
      body: JSON.stringify({ name, email, password })
    });
  },

  async login(email: string, password: string) {
    return apiRequest("/auth/login/json", {
      method: "POST",
      useToken: false,
      body: JSON.stringify({ email, password })
    });
  },

  async getMe() {
    return apiRequest("/auth/me", {
      method: "GET"
    });
  },

  // 2. Documents Management
  async listDocuments() {
    return apiRequest("/documents", {
      method: "GET"
    });
  },

  async uploadDocument(file: File, chatId?: number) {
    const formData = new FormData();
    formData.append("file", file);
    if (chatId) {
      formData.append("chat_id", chatId.toString());
    }
    return apiRequest("/upload/file", {
      method: "POST",
      body: formData
    });
  },

  async listChatDocuments(chatId: number) {
    return apiRequest(`/documents/chat/${chatId}`, {
      method: "GET"
    });
  },

  async deleteDocument(documentId: number) {
    return apiRequest(`/documents/${documentId}`, {
      method: "DELETE"
    });
  },

  // 3. Conversational QA
  async createChatSession(documentId: number | null) {
    return apiRequest("/chat/session", {
      method: "POST",
      body: JSON.stringify({ document_id: documentId })
    });
  },

  async listChatSessions() {
    return apiRequest("/chat/sessions", {
      method: "GET"
    });
  },

  async getChatHistory(chatId: number) {
    return apiRequest(`/chat/history/${chatId}`, {
      method: "GET"
    });
  },

  async sendChatMessage(chatId: number, content: string, allDocuments?: boolean) {
    return apiRequest("/chat/message", {
      method: "POST",
      body: JSON.stringify({ chat_id: chatId, content, all_documents: allDocuments })
    });
  },

  async sendChatMessageStream(chatId: number, content: string, onToken: (token: string) => void, allDocuments?: boolean) {
    const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
    const activeModel = typeof window !== "undefined" ? localStorage.getItem("activeModel") : null;
    
    const headers: Record<string, string> = {
      "Content-Type": "application/json"
    };
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    if (activeModel) {
      headers["X-Ollama-Model"] = activeModel;
    }
    
    const response = await fetch(`${API_BASE_URL}/chat/message/stream`, {
      method: "POST",
      headers,
      body: JSON.stringify({ chat_id: chatId, content, all_documents: allDocuments })
    });
    
    if (!response.ok) {
      const errText = await response.text();
      throw new Error(errText || "Streaming failed.");
    }
    
    if (!response.body) {
      throw new Error("Response body is empty.");
    }
    
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      
      // Keep the last partial line in buffer
      buffer = lines.pop() || "";
      
      for (const line of lines) {
        if (line.startsWith("data:")) {
          let tokenVal = line.substring(5);
          if (tokenVal.startsWith(" ")) {
            tokenVal = tokenVal.substring(1);
          }
          onToken(tokenVal);
        }
      }
    }
    
    // Process final leftovers
    if (buffer.startsWith("data:")) {
      let tokenVal = buffer.substring(5);
      if (tokenVal.startsWith(" ")) {
        tokenVal = tokenVal.substring(1);
      }
      onToken(tokenVal);
    }
  },

  async deleteChatSession(chatId: number) {
    return apiRequest(`/chat/session/${chatId}`, {
      method: "DELETE"
    });
  },

  // 4. Study Mode Dashboard
  async getStudyDashboard(documentId: number) {
    return apiRequest(`/study/dashboard/${documentId}`, {
      method: "GET"
    });
  },

  async generateSummary(documentId: number, regenerate: boolean = false) {
    return apiRequest(`/study/summarize/${documentId}?regenerate=${regenerate}`, {
      method: "POST"
    });
  },

  async generateQuiz(documentId: number) {
    return apiRequest(`/study/quiz/${documentId}`, {
      method: "POST"
    });
  },

  async generateFlashcards(documentId: number) {
    return apiRequest(`/study/flashcards/${documentId}`, {
      method: "POST"
    });
  },

  // 5. Online Search
  async searchOnline(query: string) {
    return apiRequest("/search/", {
      method: "POST",
      body: JSON.stringify({ query })
    });
  }
};
