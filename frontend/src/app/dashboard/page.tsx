"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "../services/api";
import { 
  LogOut, Upload, FileText, Trash2, MessageSquare, 
  Loader2, BookOpen, AlertCircle, CheckCircle, Globe, GraduationCap, Cpu, Plus, Sun, Moon
} from "lucide-react";

interface DocumentMeta {
  id: number;
  filename: string;
  language: string;
  created_at: string;
}

export default function DashboardPage() {
  const [documents, setDocuments] = useState<DocumentMeta[]>([]);
  const [chatSessions, setChatSessions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [theme, setTheme] = useState<"dark" | "light">("dark");

  useEffect(() => {
    if (typeof window !== "undefined") {
      const savedTheme = localStorage.getItem("theme") as "dark" | "light";
      if (savedTheme) {
        setTheme(savedTheme);
        if (savedTheme === "light") {
          document.documentElement.classList.add("light");
        } else {
          document.documentElement.classList.remove("light");
        }
      }
    }
  }, []);

  const toggleTheme = () => {
    const nextTheme = theme === "dark" ? "light" : "dark";
    setTheme(nextTheme);
    localStorage.setItem("theme", nextTheme);
    if (nextTheme === "light") {
      document.documentElement.classList.add("light");
    } else {
      document.documentElement.classList.remove("light");
    }
  };

  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(""); // Uploading -> Parsing -> Indexing
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [userName, setUserName] = useState("User");
  const [activeModel, setActiveModel] = useState("qwen2.5:0.5b");

  useEffect(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("activeModel");
      if (saved) {
        setActiveModel(saved);
      } else {
        localStorage.setItem("activeModel", "qwen2.5:0.5b");
      }
    }
  }, []);

  const handleModelChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const model = e.target.value;
    setActiveModel(model);
    if (typeof window !== "undefined") {
      localStorage.setItem("activeModel", model);
    }
  };
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  // Authentication & Initial load check
  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      router.push("/login");
      return;
    }
    
    const cachedName = localStorage.getItem("user_name");
    if (cachedName) setUserName(cachedName);
    
    fetchDocuments();
  }, []);

  const fetchDocuments = async () => {
    setLoading(true);
    setError("");
    try {
      const data = await api.listDocuments();
      setDocuments(data);
      
      // Fetch user's chat sessions and join them with filenames
      try {
        const sessions = await api.listChatSessions();
        const joined = sessions.map((sess: any) => {
          if (sess.document_id === null) {
            return {
              ...sess,
              filename: "General AI Assistant",
              language: "en"
            };
          }
          const doc = data.find((d: any) => d.id === sess.document_id);
          return {
            ...sess,
            filename: doc ? doc.filename : `Document #${sess.document_id}`,
            language: doc ? doc.language : "en"
          };
        });
        setChatSessions(joined);
      } catch (sessErr) {
        console.error("Failed to load chat sessions:", sessErr);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load document list.");
      // If unauthorized, redirect to login
      if (err.message.includes("401") || err.message.includes("credentials")) {
        localStorage.clear();
        router.push("/login");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.clear();
    router.push("/login");
  };

  const triggerFileSelect = () => {
    fileInputRef.current?.click();
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    
    const file = files[0];
    setError("");
    setSuccess("");
    setUploading(true);
    
    // Simulate step-by-step processing loaders for final-year project defense "wow" factor
    setUploadProgress("Uploading file to server...");
    
    try {
      // Step 1: Upload and get response (which handles backend extraction, lang detection, & FAISS embedding)
      const res = await api.uploadDocument(file);
      
      setUploadProgress("Extracting document text...");
      await new Promise(r => setTimeout(r, 800)); // Short visual pause for user feedback
      
      setUploadProgress("Computing semantic vectors and FAISS index...");
      await new Promise(r => setTimeout(r, 600)); // Short visual pause
      
      setSuccess(`"${file.name}" uploaded and processed successfully! Detected language: ${getLanguageFullName(res.language)}.`);
      
      // Refetch document list
      await fetchDocuments();
    } catch (err: any) {
      setError(err.message || "Failed to process and upload the file.");
    } finally {
      setUploading(false);
      setUploadProgress("");
      if (fileInputRef.current) fileInputRef.current.value = ""; // Clear file input
    }
  };

  const handleDeleteDocument = async (docId: number, filename: string) => {
    if (!confirm(`Are you sure you want to delete "${filename}"? This will permanently delete its FAISS vector embeddings and database records.`)) {
      return;
    }
    
    setError("");
    setSuccess("");
    try {
      await api.deleteDocument(docId);
      setSuccess(`"${filename}" deleted successfully.`);
      // Update list
      setDocuments(prev => prev.filter(d => d.id !== docId));
      setChatSessions(prev => prev.filter(s => s.document_id !== docId));
    } catch (err: any) {
      setError(err.message || "Failed to delete the document.");
    }
  };

  const handleStartChat = async (docId: number) => {
    setError("");
    try {
      const sessions = await api.listChatSessions();
      const existingSession = sessions.find((s: any) => s.document_id === docId);
      
      if (existingSession) {
        // Route directly to existing chat history
        router.push(`/chat/${existingSession.id}`);
      } else {
        // Create new session if none exists
        const chatSession = await api.createChatSession(docId);
        router.push(`/chat/${chatSession.id}`);
      }
    } catch (err: any) {
      setError(err.message || "Failed to initialize chat session.");
    }
  };

  // Helper to resolve ISO codes to readable names
  const getLanguageFullName = (code: string) => {
    const langs: Record<string, string> = {
      en: "English",
      fr: "French",
      ar: "Arabic",
      es: "Spanish",
      de: "German",
      ha: "Hausa"
    };
    return langs[code.toLowerCase()] || code.toUpperCase();
  };

  const getFormatDate = (dateStr: string) => {
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground selection:bg-primary selection:text-background">
      
      {/* Navigation Header */}
      <header className="w-full border-b border-border/10 bg-slate-950/40 backdrop-blur-md sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-6 py-4 flex justify-between items-center">
          <Link href="/" className="flex items-center space-x-2">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
              <BookOpen className="w-5 h-5 text-background font-bold" />
            </div>
            <span className="text-lg font-bold tracking-tight">
              Aura<span className="text-primary">QA</span>
            </span>
          </Link>
          
          <div className="flex items-center space-x-6">
            <div className="flex items-center space-x-2 bg-slate-900/60 border border-border/30 rounded-lg px-2.5 py-1.5 text-xs text-slate-300">
              <Cpu className="w-3.5 h-3.5 text-primary shrink-0" />
              <select 
                value={activeModel}
                onChange={handleModelChange}
                className="bg-transparent border-none outline-none font-semibold text-slate-200 cursor-pointer pr-1"
              >
                <option value="qwen2.5:0.5b" className="bg-slate-950 text-slate-200">Fast Mode (Qwen 0.5B)</option>
                <option value="gemma2:2b" className="bg-slate-950 text-slate-200">Smart Mode (Gemma 2B)</option>
              </select>
            </div>

            <div className="text-sm">
              <span className="text-slate-400">Welcome, </span>
              <span className="font-semibold text-primary">{userName}</span>
            </div>
            
            <button 
              onClick={toggleTheme}
              className="p-2 rounded-lg border border-border/30 hover:border-primary/40 hover:bg-primary/5 text-slate-400 hover:text-primary transition-all duration-200 cursor-pointer"
              title={theme === "dark" ? "Switch to Light Mode" : "Switch to Dark Mode"}
            >
              {theme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>

            <button
              onClick={handleLogout}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-border/30 hover:border-red-500/30 hover:bg-red-950/10 hover:text-red-400 text-sm font-semibold transition-all duration-200 cursor-pointer"
            >
              <LogOut className="w-4 h-4" />
              <span>Log Out</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-grow max-w-7xl w-full mx-auto px-6 py-10 space-y-10">
        
        {/* Status Messages */}
        <div className="space-y-3">
          {error && (
            <div className="p-4 rounded-xl bg-red-950/30 border border-red-900/40 text-red-200 text-sm flex items-start space-x-3">
              <AlertCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}
          {success && (
            <div className="p-4 rounded-xl bg-primary-glow/30 border border-primary/20 text-emerald-200 text-sm flex items-start space-x-3">
              <CheckCircle className="w-5 h-5 text-primary shrink-0 mt-0.5" />
              <span>{success}</span>
            </div>
          )}
        </div>

        {/* Upload Dashboard Block */}
        <section className="glass-panel p-8 rounded-2xl space-y-6 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-44 h-44 bg-primary/5 rounded-full blur-3xl pointer-events-none" />
          
          <div className="max-w-xl space-y-2">
            <h2 className="text-xl font-bold text-foreground">Upload Document</h2>
            <p className="text-sm text-slate-400">
              Select or drag-and-drop a file to ingest. Allowed formats: **PDF, DOCX, TXT, CSV**. 
              Only English, French, Arabic, Spanish, German, and Hausa texts are accepted.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-center">
            
            {/* Drag & Drop Card */}
            <div className="md:col-span-2">
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileUpload}
                accept=".pdf,.docx,.txt,.csv"
                className="hidden"
              />
              
              <div 
                onClick={triggerFileSelect}
                className={`border-2 border-dashed rounded-xl p-8 flex flex-col items-center justify-center space-y-4 cursor-pointer transition-all duration-200 ${
                  uploading 
                    ? "border-primary/20 bg-slate-900/10 pointer-events-none" 
                    : "border-border/30 bg-slate-950/20 hover:border-primary/50 hover:bg-slate-950/40"
                }`}
              >
                {uploading ? (
                  <div className="flex flex-col items-center space-y-3">
                    <Loader2 className="w-10 h-10 text-primary animate-spin" />
                    <span className="text-sm font-semibold text-slate-300">{uploadProgress}</span>
                  </div>
                ) : (
                  <>
                    <div className="w-12 h-12 rounded-full bg-primary/5 flex items-center justify-center text-primary">
                      <Upload className="w-6 h-6" />
                    </div>
                    <div className="text-center space-y-1">
                      <p className="text-sm font-semibold">Click to select document</p>
                      <p className="text-xs text-slate-500">PDF, DOCX, TXT, or CSV up to 10MB</p>
                    </div>
                  </>
                )}
              </div>
            </div>

            {/* Allowed languages check box info */}
            <div className="glass-panel-emerald p-6 rounded-xl space-y-3 h-full flex flex-col justify-center">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center space-x-1.5">
                <Globe className="w-4 h-4 text-primary" />
                <span>Multilingual Validation</span>
              </h4>
              <p className="text-xs text-slate-400 leading-relaxed">
                Our pipeline runs language classification during text extraction. Ingestion proceeds only if the document is primarily in one of the 6 supported languages.
              </p>
            </div>

          </div>
        </section>

        {/* Two-Column Grid: Library (Left) & Recent Conversations (Right) */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-10">
          
          {/* Main Column: Your Document Library (2/3 width) */}
          <section className="lg:col-span-2 space-y-6">
            <div className="flex justify-between items-center">
              <h2 className="text-xl font-bold text-foreground">Your Document Library</h2>
              <button 
                onClick={fetchDocuments}
                className="text-xs font-semibold text-primary hover:underline flex items-center space-x-1"
              >
                <span>Refresh list</span>
              </button>
            </div>

            {loading ? (
              <div className="py-20 flex justify-center items-center">
                <Loader2 className="w-10 h-10 text-primary animate-spin" />
              </div>
            ) : documents.length === 0 ? (
              <div className="py-16 text-center border border-border/20 rounded-2xl bg-card/20 space-y-4">
                <FileText className="w-12 h-12 text-slate-600 mx-auto" />
                <div className="space-y-1">
                  <h3 className="font-bold text-foreground">No documents found</h3>
                  <p className="text-sm text-slate-500 max-w-sm mx-auto">
                    Get started by uploading a file above. Once parsed, it will be vectorized in FAISS.
                  </p>
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                {documents.map((doc) => (
                  <div 
                    key={doc.id}
                    className="glass-panel p-6 rounded-xl hover:border-primary/20 transition-all duration-300 flex flex-col justify-between h-48 space-y-4"
                  >
                    <div className="space-y-3">
                      <div className="flex justify-between items-start">
                        <div className="w-9 h-9 rounded bg-slate-900/50 flex items-center justify-center text-slate-400">
                          <FileText className="w-5 h-5" />
                        </div>
                        <span className="px-2 py-0.5 rounded bg-primary/10 border border-primary/20 text-[10px] font-bold uppercase tracking-wider text-primary">
                          {getLanguageFullName(doc.language)}
                        </span>
                      </div>
                      
                      <div className="space-y-1">
                        <h4 className="font-bold text-sm truncate text-foreground" title={doc.filename}>
                          {doc.filename}
                        </h4>
                        <p className="text-[10px] text-slate-500">
                          Uploaded {getFormatDate(doc.created_at)}
                        </p>
                      </div>
                    </div>

                    {/* Actions footer */}
                    <div className="flex space-x-3 pt-2 border-t border-border/10">
                      <button
                        onClick={() => handleStartChat(doc.id)}
                        className="flex-grow flex items-center justify-center space-x-1 py-2 px-2.5 rounded bg-primary hover:bg-primary-hover text-background text-[11px] font-bold transition-all duration-150 cursor-pointer"
                      >
                        <MessageSquare className="w-3.5 h-3.5" />
                        <span>Start Chat</span>
                      </button>

                      <button
                        onClick={() => router.push(`/dashboard/study/${doc.id}`)}
                        className="flex-grow flex items-center justify-center space-x-1 py-2 px-2.5 rounded border border-primary/25 hover:border-primary/50 bg-primary/5 hover:bg-primary/10 text-primary text-[11px] font-bold transition-all duration-150 cursor-pointer"
                      >
                        <GraduationCap className="w-3.5 h-3.5" />
                        <span>Study Mode</span>
                      </button>
                      
                      <button
                        onClick={() => handleDeleteDocument(doc.id, doc.filename)}
                        className="flex items-center justify-center p-2 rounded border border-border/40 hover:border-red-500/40 hover:bg-red-950/10 hover:text-red-400 text-slate-400 transition-all duration-150 cursor-pointer"
                        title="Delete document"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>

                  </div>
                ))}
              </div>
            )}
          </section>

          {/* Sidebar Column: Recent Conversations (1/3 width) */}
          <section className="space-y-6">
            <div className="flex justify-between items-center">
              <h2 className="text-xl font-bold text-foreground flex items-center space-x-2">
                <MessageSquare className="w-5 h-5 text-primary" />
                <span>Recent Chats</span>
              </h2>
              <button
                onClick={async () => {
                  try {
                    const newSession = await api.createChatSession(null);
                    router.push(`/chat/${newSession.id}`);
                  } catch (err: any) {
                    setError(err.message || "Failed to create general chat.");
                  }
                }}
                className="text-xs font-bold text-primary border border-primary/20 bg-primary/5 hover:bg-primary/10 px-2.5 py-1.5 rounded-lg flex items-center space-x-1.5 cursor-pointer transition-colors"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>New General Chat</span>
              </button>
            </div>
            
            {chatSessions.length === 0 ? (
              <div className="p-8 text-center border border-border/20 rounded-2xl bg-card/5 space-y-3">
                <p className="text-xs text-slate-400 leading-normal">No active chat sessions found.</p>
                <p className="text-[10px] text-slate-500 leading-relaxed">
                  Start a chat session on any document to preserve history and resume later.
                </p>
              </div>
            ) : (
              <div className="space-y-4 max-h-[500px] overflow-y-auto pr-1 scrollbar">
                {chatSessions.map((session) => (
                  <div 
                    key={session.id}
                    onClick={() => router.push(`/chat/${session.id}`)}
                    className="glass-panel p-4.5 rounded-xl hover:border-primary/25 bg-slate-950/20 hover:bg-slate-950/40 cursor-pointer transition-all duration-200 flex flex-col justify-between space-y-2 group"
                  >
                    <div className="flex justify-between items-start space-x-2">
                      <h4 className="font-bold text-xs truncate text-foreground group-hover:text-primary transition-colors flex-grow" title={session.filename}>
                        {session.filename}
                      </h4>
                      <span className="px-1.5 py-0.5 rounded bg-primary/5 border border-primary/10 text-[9px] font-semibold uppercase tracking-wider text-slate-400 shrink-0">
                        {session.language.toUpperCase()}
                      </span>
                    </div>
                    <p className="text-[9px] text-slate-500">
                      Resume Chat Session #{session.id}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </section>

        </div>

      </main>
    </div>
  );
}
