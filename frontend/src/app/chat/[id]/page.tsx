"use client";

import React, { useEffect, useState, useRef, use } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "../../services/api";
import { 
  ArrowLeft, Send, Loader2, BookOpen, User, Bot, 
  Search, ShieldAlert, Sparkles, FileText, Globe, AlertTriangle, Cpu,
  Trash2, Plus, Moon, Sun, Home, Paperclip, Menu
} from "lucide-react";

interface SourceDetail {
  page_number?: number;
  score?: number;
  title?: string;
  url?: string;
}

interface ChatMessage {
  id: string | number;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  sources?: SourceDetail[];
  max_score?: number;
  out_of_scope?: boolean;
  label?: string;
}

interface DocumentMeta {
  id: number;
  filename: string;
  language: string;
  created_at: string;
}

interface ChatSession {
  id: number;
  document_id: number | null;
  user_id: number;
}

interface ChatPageProps {
  params: Promise<{ id: string }>;
}

const formatTextWithBold = (text: string) => {
  if (!text) return "";
  const parts = text.split(/\*\*([\s\S]*?)\*\*/g);
  return parts.map((part, i) => {
    if (i % 2 === 1) {
      return <strong key={i} className="font-extrabold text-primary">{part}</strong>;
    }
    return part;
  });
};

export default function ChatPage({ params }: ChatPageProps) {
  const resolvedParams = use(params);
  const chatId = parseInt(resolvedParams.id, 10);

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputText, setInputText] = useState("");
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  
  // Theme and UI states
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  const [userName, setUserName] = useState("User");
  const [activeModel, setActiveModel] = useState("qwen2.5:0.5b");

  // Sidebar states
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [documents, setDocuments] = useState<DocumentMeta[]>([]);
  const [loadingSessions, setLoadingSessions] = useState(true);

  // Active document state (null for general chat)
  const [activeDoc, setActiveDoc] = useState<DocumentMeta | null>(null);
  const [chatDocs, setChatDocs] = useState<DocumentMeta[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  // Library Search and Dynamic Upload states
  const [mounted, setMounted] = useState(false);
  const [allDocuments, setAllDocuments] = useState(false);
  const [uploadingFiles, setUploadingFiles] = useState<{ id: string; name: string; progress: string }[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  // Scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, sending]);

  // Auto-resize textarea height as content changes
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
    }
  }, [inputText]);

  // Load theme preference on mount
  useEffect(() => {
    setMounted(true);
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
      
      const savedModel = localStorage.getItem("activeModel");
      if (savedModel) {
        setActiveModel(savedModel);
      } else {
        localStorage.setItem("activeModel", "qwen2.5:0.5b");
      }

      const savedSidebar = localStorage.getItem("sidebarOpen");
      if (savedSidebar !== null) {
        setSidebarOpen(savedSidebar === "true");
      }
    }
  }, []);

  const toggleSidebar = () => {
    const nextState = !sidebarOpen;
    setSidebarOpen(nextState);
    if (typeof window !== "undefined") {
      localStorage.setItem("sidebarOpen", String(nextState));
    }
  };

  // Auth check & load initial data
  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      router.push("/login");
      return;
    }

    const cachedName = localStorage.getItem("user_name");
    if (cachedName) setUserName(cachedName);

    loadSessionAndHistory();
    loadSidebarSessions();
  }, [chatId]);

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

  const handleModelChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const model = e.target.value;
    setActiveModel(model);
    if (typeof window !== "undefined") {
      localStorage.setItem("activeModel", model);
    }
  };

  // Load all user documents and chat sessions for the sidebar list
  const loadSidebarSessions = async () => {
    setLoadingSessions(true);
    try {
      const docs = await api.listDocuments();
      setDocuments(docs);
      const chats = await api.listChatSessions();
      // Reverse list to show newest chats first
      setSessions([...chats].reverse());
    } catch (err) {
      console.error("Failed to fetch sidebar sessions:", err);
    } finally {
      setLoadingSessions(false);
    }
  };

  // Load messages history for active chat and link the document
  const loadSessionAndHistory = async (silent = false) => {
    if (!silent) setLoadingHistory(true);
    setError("");
    try {
      const sessionsList: ChatSession[] = await api.listChatSessions();
      const currentSession = sessionsList.find(s => s.id === chatId);

      if (!currentSession) {
        throw new Error("Chat session not found or access denied.");
      }

      if (currentSession.document_id !== null) {
        const docs: DocumentMeta[] = await api.listDocuments();
        const currentDoc = docs.find(d => d.id === currentSession.document_id);
        if (currentDoc) {
          setActiveDoc(currentDoc);
        } else {
          setActiveDoc(null);
        }
      } else {
        setActiveDoc(null);
      }

      // Load in-chat documents
      try {
        const inChatDocs = await api.listChatDocuments(chatId);
        setChatDocs(inChatDocs);
      } catch (inChatErr) {
        console.error("Failed to load in-chat documents:", inChatErr);
      }

      const history = await api.getChatHistory(chatId);
      const formattedHistory: ChatMessage[] = history.map((msg: any) => {
        const isOutOfScope = msg.role === "assistant" && (
          msg.content.includes("not available in the uploaded document") || 
          msg.content.includes("outside the scope") ||
          msg.content.includes("out of the scope") ||
          msg.content.includes("hors de portée") ||
          msg.content.includes("fuera del alcance") ||
          msg.content.includes("außerhalb") ||
          msg.content.includes("خارج نطاق") ||
          msg.content.includes("waje da")
        );
        return {
          id: msg.id,
          role: msg.role,
          content: msg.content,
          timestamp: msg.timestamp,
          out_of_scope: isOutOfScope
        };
      });
      setMessages(formattedHistory);
    } catch (err: any) {
      setError(err.message || "Failed to initialize chat.");
      if (err.message.includes("401") || err.message.includes("credentials")) {
        localStorage.clear();
        router.push("/login");
      }
    } finally {
      if (!silent) setLoadingHistory(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (inputText.trim() && !sending && uploadingFiles.length === 0) {
        const form = e.currentTarget.form;
        if (form) {
          form.requestSubmit();
        }
      }
    }
  };

  // Handle new message sending (SSE Token Streaming)
  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() || sending) return;

    const query = inputText.trim();
    setInputText("");
    setSending(true);
    setError("");

    // Append User message locally
    const userTempMessage: ChatMessage = {
      id: `user-temp-${Date.now()}`,
      role: "user",
      content: query,
      timestamp: new Date().toISOString()
    };
    
    // Append blank Assistant message to hold streamed tokens
    const assistantTempId = `assistant-stream-${Date.now()}`;
    const assistantTempMessage: ChatMessage = {
      id: assistantTempId,
      role: "assistant",
      content: "",
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userTempMessage, assistantTempMessage]);

    let accumulatedAnswer = "";
    try {
      // Call token streaming API helper
      await api.sendChatMessageStream(
        chatId,
        query,
        (token) => {
          accumulatedAnswer += token;
          // Update local state with accumulated chunks
          setMessages(prev => 
            prev.map(m => 
              m.id === assistantTempId 
                ? { ...m, content: accumulatedAnswer } 
                : m
            )
          );
        },
        activeDoc === null ? allDocuments : false
      );
    } catch (err: any) {
      setError(err.message || "Failed to deliver message stream.");
      // Rollback temporary assistant message if nothing arrived
      if (!accumulatedAnswer) {
        setMessages(prev => prev.filter(m => m.id !== userTempMessage.id && m.id !== assistantTempId));
      }
    } finally {
      setSending(false);
      // Reload final settled history in background (silent=true) to populate citations/out-of-scope flags
      loadSessionAndHistory(true);
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size > 5 * 1024 * 1024) {
      setError("File size exceeds 5MB limit.");
      return;
    }

    const uploadId = `upload-${Date.now()}`;
    setUploadingFiles(prev => [...prev, { id: uploadId, name: file.name, progress: "Uploading..." }]);
    setError("");

    try {
      await api.uploadDocument(file, chatId);
      // Reload in-chat documents
      const inChatFiles = await api.listChatDocuments(chatId);
      setChatDocs(inChatFiles);
      await loadSidebarSessions();
    } catch (err: any) {
      setError(err.message || "Failed to upload document.");
    } finally {
      setUploadingFiles(prev => prev.filter(f => f.id !== uploadId));
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const handleDeleteChatDocument = async (docId: number, filename: string) => {
    if (!confirm(`Are you sure you want to remove "${filename}" from this chat session?`)) return;
    setError("");
    try {
      await api.deleteDocument(docId);
      setChatDocs(prev => prev.filter(d => d.id !== docId));
    } catch (err: any) {
      setError(err.message || "Failed to remove document.");
    }
  };

  // Create a new general-purpose chat session (document_id = null)
  const handleCreateNewChat = async () => {
    setError("");
    try {
      const newSession = await api.createChatSession(null);
      await loadSidebarSessions();
      router.push(`/chat/${newSession.id}`);
    } catch (err: any) {
      setError(err.message || "Failed to create general chat session.");
    }
  };

  // Delete a chat session
  const handleDeleteSession = async (e: React.MouseEvent, idToDelete: number) => {
    e.preventDefault();
    e.stopPropagation();
    if (!confirm("Are you sure you want to delete this chat session?")) return;

    try {
      await api.deleteChatSession(idToDelete);
      await loadSidebarSessions();
      
      // If we deleted the active chat, redirect to dashboard or another chat
      if (idToDelete === chatId) {
        router.push("/dashboard");
      }
    } catch (err: any) {
      setError(err.message || "Failed to delete chat session.");
    }
  };

  const handleOnlineSearch = (queryText: string) => {
    if (typeof window !== "undefined") {
      const searchUrl = `https://www.google.com/search?q=${encodeURIComponent(queryText)}`;
      window.open(searchUrl, "_blank", "noopener,noreferrer");
    }
  };

  const handleAuraSearch = async (queryText: string) => {
    if (sending) return;
    setSending(true);
    setError("");

    try {
      const res = await api.searchOnline(queryText);
      const assistantMessage: ChatMessage = {
        id: `assistant-search-${Date.now()}`,
        role: "assistant",
        content: res.answer,
        timestamp: new Date().toISOString(),
        sources: res.sources,
        label: res.label
      };
      setMessages(prev => [...prev, assistantMessage]);
    } catch (err: any) {
      setError(err.message || "Failed to query online search services.");
    } finally {
      setSending(false);
    }
  };

  // Resolve document filenames for the sidebar sessions list
  const getSessionTitle = (session: ChatSession) => {
    if (session.document_id === null) {
      return "General AI Assistant";
    }
    const doc = documents.find(d => d.id === session.document_id);
    return doc ? doc.filename : `Document Chat #${session.id}`;
  };

  // Helper to format ISO codes to readable names
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

  const formatTime = (isoString: string) => {
    try {
      const date = new Date(isoString);
      return date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
    } catch {
      return "";
    }
  };

  return (
    <div className="min-h-screen flex bg-background text-foreground transition-colors duration-200">
      
      {/* 1. Left Navigation Sidebar Panel */}
      <aside className={`transition-all duration-300 ease-in-out border-r layout-border bg-sidebar flex flex-col h-screen shrink-0 relative z-20 ${
        sidebarOpen ? "w-80" : "w-16"
      }`}>
        
        {/* Sidebar Header Logo & Create Button */}
        <div className={`border-b layout-border flex flex-col ${sidebarOpen ? "p-5 space-y-4" : "py-5 px-2 space-y-4 items-center"}`}>
          <div className={`flex items-center ${sidebarOpen ? "justify-between" : "justify-center"}`}>
            {sidebarOpen && (
              <Link href="/dashboard" className="flex items-center space-x-2 shrink-0">
                <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center shadow-md shadow-primary/20">
                  <BookOpen className="w-4.5 h-4.5 text-slate-950 font-bold" />
                </div>
                <span className="font-extrabold text-lg tracking-tight">
                  Aura<span className="text-primary">QA</span>
                </span>
              </Link>
            )}
            
            {/* Sidebar toggle button inside the sidebar itself */}
            <button 
              type="button"
              onClick={toggleSidebar}
              className={`p-2.5 rounded-xl border border-border/30 hover:border-primary/40 hover:bg-primary/5 text-slate-400 hover:text-primary transition-all duration-200 cursor-pointer flex items-center justify-center ${sidebarOpen ? "" : "w-10 h-10"}`}
              title={sidebarOpen ? "Collapse sidebar" : "Expand sidebar"}
            >
              <Menu className="w-4.5 h-4.5" />
            </button>
          </div>

          {/* New Chat Trigger */}
          {sidebarOpen ? (
            <button
              onClick={handleCreateNewChat}
              className="w-full py-3.5 px-4 rounded-xl bg-primary hover:bg-primary-hover text-slate-950 font-bold shadow-md shadow-primary/10 hover:shadow-primary/25 transition-all duration-200 flex items-center justify-center space-x-2 text-sm cursor-pointer shrink-0"
            >
              <Plus className="w-4 h-4" />
              <span>New General Chat</span>
            </button>
          ) : (
            <button
              onClick={handleCreateNewChat}
              className="w-10 h-10 rounded-full bg-primary hover:bg-primary-hover text-slate-950 font-bold shadow-md shadow-primary/10 hover:shadow-primary/25 transition-all duration-200 flex items-center justify-center cursor-pointer shrink-0"
              title="New General Chat"
            >
              <Plus className="w-5 h-5" />
            </button>
          )}
        </div>

        {/* Sessions Scroll List */}
        <div className={`flex-1 min-h-0 overflow-y-auto py-4 scrollbar ${sidebarOpen ? "px-3 space-y-2" : "px-2 space-y-3"}`}>
          {sidebarOpen && (
            <div className="px-3 mb-2">
              <span className="text-[10px] font-bold text-muted uppercase tracking-wider">Chat History</span>
            </div>
          )}

          {loadingSessions ? (
            <div className="py-8 flex justify-center">
              <Loader2 className="w-5 h-5 text-primary animate-spin" />
            </div>
          ) : sessions.length === 0 ? (
            sidebarOpen ? (
              <div className="text-center py-6 px-4 text-xs text-slate-500">
                No recent conversations.
              </div>
            ) : null
          ) : (
            sessions.map((sess) => {
              const isActive = sess.id === chatId;
              if (sidebarOpen) {
                return (
                  <div 
                    key={sess.id}
                    className={`group relative rounded-xl border transition-all duration-150 flex items-center ${
                      isActive 
                        ? "bg-primary/10 border-primary/25 text-primary shadow-sm"
                        : "border-transparent hover:border-border/30 hover:bg-card text-muted hover:text-foreground"
                    }`}
                  >
                    <Link 
                      href={`/chat/${sess.id}`}
                      className="flex-grow py-3 px-3.5 pr-10 text-xs font-semibold truncate select-none block"
                      title={getSessionTitle(sess)}
                    >
                      {sess.document_id === null ? "🌐 " : "📄 "}
                      {getSessionTitle(sess)}
                    </Link>
                    
                    {/* Delete Option */}
                    <button
                      onClick={(e) => handleDeleteSession(e, sess.id)}
                      className="absolute right-2 p-1.5 rounded-lg opacity-0 group-hover:opacity-100 hover:bg-red-500/10 text-slate-500 hover:text-red-400 transition-all duration-150 cursor-pointer"
                      title="Delete Chat"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                );
              } else {
                return (
                  <Link 
                    key={sess.id}
                    href={`/chat/${sess.id}`}
                    className={`w-10 h-10 rounded-xl flex items-center justify-center transition-all duration-150 mx-auto ${
                      isActive 
                        ? "bg-primary/10 border border-primary/25 text-primary shadow-sm"
                        : "border border-transparent hover:border-border/30 hover:bg-card text-muted hover:text-foreground"
                    }`}
                    title={getSessionTitle(sess)}
                  >
                    {sess.document_id === null ? <Globe className="w-4.5 h-4.5" /> : <FileText className="w-4.5 h-4.5" />}
                  </Link>
                );
              }
            })
          )}
        </div>

        {/* Sidebar Footer Info */}
        <div className={`p-4 border-t layout-border flex flex-col bg-card/10 ${sidebarOpen ? "space-y-4" : "py-4 px-2 space-y-3.5 items-center shrink-0"}`}>
          {sidebarOpen ? (
            <>
              <div className="w-full flex justify-between items-center text-[10px] text-slate-500">
                <span>Client Candidate Profile</span>
                <Link href="/dashboard" className="hover:text-primary transition-colors flex items-center space-x-1">
                  <Home className="w-3 h-3" />
                  <span>Dashboard</span>
                </Link>
              </div>
              
              {/* Theme Toggle Button */}
              <button 
                onClick={toggleTheme}
                className="w-full py-2.5 px-3 rounded-lg border border-border/30 hover:border-primary/40 hover:bg-primary/5 text-slate-400 hover:text-primary transition-all duration-200 cursor-pointer flex items-center justify-center space-x-2 text-xs"
                title={theme === "dark" ? "Switch to Light Mode" : "Switch to Dark Mode"}
              >
                {theme === "dark" ? <Sun className="w-3.5 h-3.5" /> : <Moon className="w-3.5 h-3.5" />}
                <span>{theme === "dark" ? "Light Mode" : "Dark Mode"}</span>
              </button>
            </>
          ) : (
            <div className="flex flex-col space-y-3.5 items-center">
              <Link 
                href="/dashboard" 
                className="w-10 h-10 rounded-lg hover:bg-primary/5 text-slate-400 hover:text-primary transition-all duration-150 flex items-center justify-center"
                title="Dashboard"
              >
                <Home className="w-4.5 h-4.5" />
              </Link>
              
              <button 
                onClick={toggleTheme}
                className="w-10 h-10 rounded-lg hover:bg-primary/5 text-slate-400 hover:text-primary transition-all duration-150 flex items-center justify-center cursor-pointer"
                title={theme === "dark" ? "Light Mode" : "Dark Mode"}
              >
                {theme === "dark" ? <Sun className="w-4.5 h-4.5" /> : <Moon className="w-4.5 h-4.5" />}
              </button>
              
              <div 
                className="w-10 h-10 rounded-lg bg-primary/10 border border-primary/20 text-primary flex items-center justify-center text-xs font-bold"
                title={`User: ${userName}`}
              >
                <User className="w-4 h-4" />
              </div>
            </div>
          )}
        </div>
      </aside>

      {/* 2. Main Conversational Frame */}
      <main className="flex-grow flex flex-col h-screen overflow-hidden relative">
        
        {/* Decorative Light Theme backgrounds */}
        <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] rounded-full bg-primary/5 blur-[120px] pointer-events-none" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] rounded-full bg-primary/2 blur-[120px] pointer-events-none" />

        {/* Upper Navigation Header */}
        <header className="w-full border-b layout-border bg-card/30 backdrop-blur-md py-4 px-6 flex items-center justify-between sticky top-0 z-10">
          <div className="flex items-center space-x-3.5">
            <Link 
              href="/dashboard"
              className="flex items-center justify-center p-2.5 rounded-xl border border-border/30 hover:border-primary/40 hover:bg-primary/5 text-slate-400 hover:text-primary transition-all duration-200 md:hidden"
            >
              <ArrowLeft className="w-4 h-4" />
            </Link>
            
            <div className="flex items-center space-x-3">
              <div className="w-9 h-9 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center text-primary">
                {activeDoc ? <FileText className="w-5 h-5" /> : <Bot className="w-5 h-5" />}
              </div>
              <div>
                <h2 className="font-bold text-sm text-foreground max-w-xs sm:max-w-md truncate" title={activeDoc?.filename || "General AI Assistant"}>
                  {activeDoc ? activeDoc.filename : "General AI Assistant"}
                </h2>
                {activeDoc ? (
                  <p className="text-[10px] text-muted flex items-center space-x-1">
                    <Globe className="w-3 h-3 text-primary" />
                    <span>Document Grounding: {getLanguageFullName(activeDoc.language)}</span>
                  </p>
                ) : (
                  <p className="text-[10px] text-muted flex items-center space-x-1">
                    <Sparkles className="w-3 h-3 text-primary" />
                    <span>Free-form conversation mode</span>
                  </p>
                )}
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-4">
            {activeDoc === null && (
              <div className="flex items-center space-x-2 bg-card/60 border border-border/30 rounded-xl px-3 py-1.5 text-xs">
                <Globe className={`w-3.5 h-3.5 transition-colors duration-200 ${allDocuments ? 'text-primary' : 'text-slate-400'}`} />
                <span className="font-semibold text-foreground mr-1 select-none">Search library</span>
                <button
                  type="button"
                  onClick={() => setAllDocuments(!allDocuments)}
                  className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                    allDocuments ? "bg-primary" : "bg-slate-700"
                  }`}
                >
                  <span
                    className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-slate-900 shadow-md ring-0 transition duration-200 ease-in-out ${
                      allDocuments ? "translate-x-4 bg-slate-950" : "translate-x-0"
                    }`}
                  />
                </button>
              </div>
            )}

            <div className="flex items-center space-x-2 bg-card/60 border border-border/30 rounded-xl px-3 py-1.5 text-xs">
              <Cpu className="w-3.5 h-3.5 text-primary shrink-0 animate-pulse" />
              <select 
                value={activeModel}
                onChange={handleModelChange}
                className="bg-transparent border-none outline-none font-semibold text-foreground cursor-pointer pr-1"
              >
                <option value="qwen2.5:0.5b" className="bg-background text-foreground">Fast Mode (Qwen 0.5B)</option>
                <option value="gemma2:2b" className="bg-background text-foreground">Smart Mode (Gemma 2B)</option>
              </select>
            </div>
            <div className="text-xs text-muted hidden sm:block">
              Welcome, <span className="font-semibold text-primary">{userName}</span>
            </div>
          </div>
        </header>

        {/* In-Chat Documents Chip Row has been moved to form inputs preview */}

        {/* Message Thread Area */}
        <div className="flex-1 min-h-0 overflow-y-auto px-6 pt-20 pb-28 space-y-6 scrollbar">
          {error && (
            <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/25 text-red-200 text-sm flex items-start space-x-3 max-w-3xl mx-auto">
              <AlertTriangle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {loadingHistory ? (
            <div className="h-full flex flex-col justify-center items-center space-y-3">
              <Loader2 className="w-10 h-10 text-primary animate-spin" />
              <span className="text-sm text-slate-400">Loading conversation history...</span>
            </div>
          ) : messages.length === 0 ? (
            <div className="h-full flex flex-col justify-center items-center text-center max-w-md mx-auto space-y-6">
              <div className="w-16 h-16 rounded-full bg-primary/5 flex items-center justify-center text-primary">
                {activeDoc ? <FileText className="w-8 h-8" /> : <Bot className="w-8 h-8" />}
              </div>
              <div className="space-y-2">
                <h3 className="text-lg font-bold">
                  {activeDoc ? "Document Context Loaded" : "General Chat Workspace Ready"}
                </h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  {activeDoc 
                    ? `Start conversing with '${activeDoc.filename}' in any of the 6 supported languages. AuraQA will retrieve document passages in real-time, validate correctness, and ground model responses.`
                    : "Ask questions, brainstorm, or explore concepts. AuraQA is running fully offline with Llama architectures on your local client CPU to protect data sovereignty."
                  }
                </p>
              </div>
            </div>
          ) : (
            <div className="max-w-3xl mx-auto space-y-6">
              {messages.map((msg, index) => (
                <div 
                  key={msg.id || index}
                  className={`flex items-start space-x-3.5 max-w-[85%] ${
                    msg.role === "user" ? "ml-auto flex-row-reverse space-x-reverse" : "mr-auto"
                  }`}
                >
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 border ${
                    msg.role === "user" 
                      ? "bg-card border-border/30 text-slate-400" 
                      : "bg-primary/10 border-primary/20 text-primary"
                  }`}>
                    {msg.role === "user" ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                  </div>

                  <div className="space-y-2">
                    <div className={`p-4 rounded-2xl text-sm leading-relaxed whitespace-pre-line ${
                      msg.role === "user"
                        ? "bg-primary/10 border border-primary/25 text-foreground rounded-tr-none"
                        : "bg-card border layout-border text-foreground rounded-tl-none"
                    }`}>
                      {msg.role === "assistant" && msg.label && (
                        <div className="mb-2 text-[9px] font-bold tracking-wider uppercase text-sky-400 flex items-center space-x-1">
                          <Globe className="w-3.5 h-3.5" />
                          <span>{msg.label}</span>
                        </div>
                      )}
                      
                      {msg.content ? (
                        formatTextWithBold(msg.content)
                      ) : (
                        <span className="flex items-center space-x-1 text-slate-400">
                          <Loader2 className="w-3 h-3 animate-spin text-primary" />
                          <span>typing...</span>
                        </span>
                      )}
                      
                      {/* Grounding Citations */}
                      {msg.role === "assistant" && msg.sources && msg.sources.length > 0 && (
                        <div className="mt-3.5 pt-3 border-t border-border/10 space-y-2">
                          <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                            Grounded References:
                          </p>
                          <div className="flex flex-wrap gap-1.5">
                            {msg.sources.map((src, i) => {
                              if (src.url) {
                                return (
                                  <a 
                                    key={i}
                                    href={src.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="inline-flex items-center px-2 py-0.5 rounded bg-sky-950/45 border border-sky-900/40 text-[10px] font-semibold text-sky-300 hover:text-sky-100 transition-colors"
                                    title={src.title}
                                  >
                                    [{i + 1}] {src.title || "Web Link"}
                                  </a>
                                );
                              }
                              return (
                                <span 
                                  key={i} 
                                  className="inline-flex items-center px-2 py-0.5 rounded bg-background border border-border/30 text-[10px] font-semibold text-slate-300"
                                  title={`FAISS Score: ${src.score}`}
                                >
                                  Page/Row {src.page_number} <span className="text-primary ml-1.5">{src.score ? (src.score * 100).toFixed(0) : "0"}% match</span>
                                </span>
                              );
                            })}
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Grounding Shield trigger block */}
                    {msg.role === "assistant" && msg.out_of_scope && (
                      <div className="p-4.5 rounded-xl border border-amber-500/10 bg-amber-500/5 text-amber-200 text-xs space-y-3 max-w-md">
                        <div className="flex items-center space-x-2">
                          <Search className="w-4 h-4 text-amber-400 animate-pulse" />
                          <span className="font-bold text-amber-300">Out-of-Scope Shield Triggered</span>
                        </div>
                        <p className="text-slate-400 leading-relaxed">
                          Query similarity match score fell below threshold ({msg.max_score ? (msg.max_score * 100).toFixed(0) : "0"}% max similarity). LLM generation was bypassed to prevent hallucinations.
                        </p>
                        
                        <div className="flex flex-wrap gap-2.5 pt-1">
                          <button
                            type="button"
                            onClick={() => {
                              const userQuery = messages[index - 1]?.content || "";
                              handleAuraSearch(userQuery);
                            }}
                            className="flex items-center space-x-1.5 px-3 py-2 rounded bg-amber-500 hover:bg-amber-600 text-slate-950 font-bold transition-all duration-150 cursor-pointer text-xs"
                          >
                            <Globe className="w-3.5 h-3.5" />
                            <span>Search Online via AuraQA</span>
                          </button>
                          
                          <button
                            type="button"
                            onClick={() => {
                              const userQuery = messages[index - 1]?.content || "";
                              handleOnlineSearch(userQuery);
                            }}
                            className="flex items-center space-x-1.5 px-3 py-2 rounded border border-amber-500/35 hover:bg-amber-500/10 text-amber-400 font-semibold transition-all duration-150 cursor-pointer text-xs"
                          >
                            <Search className="w-3.5 h-3.5" />
                            <span>Search on Google</span>
                          </button>
                        </div>
                      </div>
                    )}

                    <p className={`text-[9px] text-muted ${msg.role === "user" ? "text-right" : "text-left"}`}>
                      {formatTime(msg.timestamp)}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Form Panel */}
        <div className="absolute bottom-0 left-0 right-0 px-6 pb-4 pt-2 bg-transparent z-10 pointer-events-none">
          <form onSubmit={handleSendMessage} className="max-w-3xl mx-auto pointer-events-auto">
            {/* dynamic uploaded & uploading files preview chip row */}
            {activeDoc === null && (chatDocs.length > 0 || uploadingFiles.length > 0) && (
              <div className="flex flex-wrap items-center gap-2 mb-2 select-none">
                {chatDocs.map((doc) => (
                  <div 
                    key={doc.id} 
                    className="flex items-center space-x-1.5 px-3 py-1 rounded-lg bg-primary/10 border border-primary/20 text-xs text-primary font-bold transition-all duration-150"
                  >
                    <FileText className="w-3.5 h-3.5" />
                    <span className="max-w-[150px] truncate" title={doc.filename}>{doc.filename}</span>
                    <button 
                      type="button"
                      onClick={() => handleDeleteChatDocument(doc.id, doc.filename)}
                      className="hover:text-red-400 transition-colors ml-1 font-bold text-sm cursor-pointer border-none bg-transparent outline-none p-0 line-none leading-none"
                      title="Remove file"
                    >
                      ×
                    </button>
                  </div>
                ))}
                {uploadingFiles.map((upFile) => (
                  <div 
                    key={upFile.id} 
                    className="flex items-center space-x-1.5 px-3 py-1 rounded-lg bg-slate-500/10 border border-slate-500/20 text-xs text-slate-400 font-bold transition-all duration-150 animate-pulse"
                  >
                    <Loader2 className="w-3 h-3 animate-spin text-slate-400" />
                    <span className="max-w-[150px] truncate" title={upFile.name}>{upFile.name}</span>
                    <span className="text-[10px] text-slate-500 font-normal">({upFile.progress})</span>
                  </div>
                ))}
              </div>
            )}

            <div className={`relative flex items-end w-full bg-background border border-border/30 rounded-xl focus-within:border-primary/50 transition-all duration-200 ${
              activeDoc === null ? "pl-11" : "pl-3.5"
            }`}>
              {/* Paperclip Button for Dynamic File Upload (General Chat only) */}
              {activeDoc === null && (
                <>
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={loadingHistory || sending || uploadingFiles.length > 0}
                    className="absolute left-2.5 bottom-1.5 p-1.5 rounded-lg border border-border/30 hover:border-primary/45 text-slate-400 hover:text-primary transition-all duration-200 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                    title="Upload file to library"
                  >
                    <Paperclip className="w-4 h-4" />
                  </button>
                  <input
                    type="file"
                    ref={fileInputRef}
                    onChange={handleFileChange}
                    accept=".pdf,.docx,.txt,.csv"
                    className="hidden"
                  />
                </>
              )}

              <textarea
                ref={textareaRef}
                rows={1}
                disabled={loadingHistory || sending || uploadingFiles.length > 0}
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={
                  activeDoc 
                    ? "Ask a question about this document..." 
                    : allDocuments 
                      ? "Search library and chat..." 
                      : "Type your query here..."
                }
                className="w-full bg-transparent border-none outline-none py-2.5 pr-14 focus:ring-0 focus:outline-none text-sm text-foreground placeholder-slate-500 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed resize-none max-h-48 overflow-y-auto scrollbar"
              />
              
              <button
                type="submit"
                disabled={!inputText.trim() || sending || uploadingFiles.length > 0}
                className="absolute right-2 bottom-1.5 px-3 py-2 bg-primary hover:bg-primary-hover disabled:bg-card disabled:text-slate-600 rounded-lg text-slate-950 transition-all duration-150 flex items-center justify-center cursor-pointer font-bold"
              >
                {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              </button>
            </div>
            <p className="text-[10px] text-muted text-center mt-1.5 leading-normal">
              {activeDoc 
                ? "Local grounding index checks Cosine vector similarity (k=5). Safe, offline-isolated local deployment."
                : allDocuments
                  ? "Searching across all library documents. Safe, offline-isolated local deployment."
                  : "General conversation mode. Completely secure, private, and running locally."
              }
            </p>
          </form>
        </div>

      </main>
    </div>
  );
}
