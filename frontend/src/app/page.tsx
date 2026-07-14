"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { FileText, Languages, Cpu, ShieldAlert, ArrowRight, BookOpen, Sun, Moon } from "lucide-react";

export default function LandingPage() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [theme, setTheme] = useState<"dark" | "light">("dark");

  useEffect(() => {
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("token");
      setIsLoggedIn(!!token);
      
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

  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground selection:bg-primary selection:text-background relative overflow-hidden">
      {/* Decorative background glow circles */}
      <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] rounded-full bg-primary/10 blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] rounded-full bg-primary/5 blur-[120px] pointer-events-none" />

      {/* Header */}
      <header className="w-full max-w-7xl mx-auto px-6 py-6 flex justify-between items-center z-10">
        <div className="flex items-center space-x-2.5">
          <div className="w-9 h-9 rounded-lg bg-primary flex items-center justify-center shadow-lg shadow-primary/20">
            <BookOpen className="w-5 h-5 text-background font-bold" />
          </div>
          <span className="text-xl font-bold tracking-tight text-foreground">
            Aura<span className="text-primary">QA</span>
          </span>
        </div>
        
        <nav className="flex items-center space-x-4">
          <button 
            onClick={toggleTheme}
            className="p-2 rounded-lg border border-border/30 hover:border-primary/40 hover:bg-primary/5 text-slate-450 hover:text-primary transition-all duration-200 cursor-pointer mr-2"
            title={theme === "dark" ? "Switch to Light Mode" : "Switch to Dark Mode"}
          >
            {theme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>

          {isLoggedIn ? (
            <Link
              href="/dashboard"
              className="px-5 py-2.5 rounded-lg bg-primary hover:bg-primary-hover text-background font-semibold transition-all duration-200 shadow-md shadow-primary/10 flex items-center space-x-1"
            >
              <span>Go to Dashboard</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
          ) : (
            <>
              <Link
                href="/login"
                className="px-4 py-2 text-sm font-medium hover:text-primary transition-all duration-200"
              >
                Log In
              </Link>
              <Link
                href="/register"
                className="px-4 py-2 text-sm font-medium rounded-lg border border-border bg-card/50 hover:bg-card hover:border-primary/30 transition-all duration-200"
              >
                Sign Up
              </Link>
            </>
          )}
        </nav>
      </header>

      {/* Main Content */}
      <main className="flex-grow flex flex-col justify-center max-w-7xl mx-auto px-6 py-12 md:py-20 z-10">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          
          {/* Hero text */}
          <div className="lg:col-span-7 space-y-8 text-center lg:text-left">
            <div className="inline-flex items-center space-x-2 px-3 py-1.5 rounded-full glass-panel border border-border/50 text-xs font-semibold text-primary">
              <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
              <span>Phase 4 RAG Complete (Local Llama 3)</span>
            </div>
            
            <h1 className="text-4xl sm:text-5xl md:text-6xl font-extrabold tracking-tight leading-tight">
              Analyze Documents, <br />
              <span className="emerald-gradient-text">Converse Privately</span>
            </h1>
            
            <p className="text-base sm:text-lg text-slate-400 max-w-xl mx-auto lg:mx-0 leading-relaxed">
              Upload your PDFs, DOCX, TXT, and CSV files and get instant answers. 
              Powered by local vector search and Llama 3. Runs 100% locally to protect your data privacy.
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center lg:justify-start gap-4">
              {isLoggedIn ? (
                <Link
                  href="/dashboard"
                  className="w-full sm:w-auto px-8 py-4 rounded-lg bg-primary hover:bg-primary-hover text-background font-bold transition-all duration-200 shadow-lg shadow-primary/10 flex items-center justify-center space-x-2 text-center"
                >
                  <span>Launch Workspace</span>
                  <ArrowRight className="w-5 h-5" />
                </Link>
              ) : (
                <>
                  <Link
                    href="/register"
                    className="w-full sm:w-auto px-8 py-4 rounded-lg bg-primary hover:bg-primary-hover text-background font-bold transition-all duration-200 shadow-lg shadow-primary/10 flex items-center justify-center space-x-2 text-center"
                  >
                    <span>Get Started Free</span>
                    <ArrowRight className="w-5 h-5" />
                  </Link>
                  <Link
                    href="/login"
                    className="w-full sm:w-auto px-8 py-4 rounded-lg border border-border bg-card/30 hover:bg-card/65 hover:border-primary/20 text-foreground font-semibold transition-all duration-200 text-center"
                  >
                    Watch Demo
                  </Link>
                </>
              )}
            </div>
            
            {/* Whitelisted languages */}
            <div className="pt-6 space-y-2.5">
              <p className="text-xs uppercase tracking-wider text-slate-500 font-semibold">
                Natively Supporting Six Whitelisted Languages:
              </p>
              <div className="flex flex-wrap justify-center lg:justify-start gap-2">
                {["English", "French", "Arabic", "Spanish", "German", "Hausa"].map((lang) => (
                  <span
                    key={lang}
                    className="px-2.5 py-1 rounded bg-card border border-border/40 text-xs font-medium text-slate-300"
                  >
                    {lang}
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* Features Grid */}
          <div className="lg:col-span-5 grid grid-cols-1 sm:grid-cols-2 gap-4">
            
            <div className="glass-panel-emerald p-6 rounded-xl space-y-4 hover:border-primary/30 transition-all duration-300">
              <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
                <FileText className="w-5 h-5" />
              </div>
              <h3 className="font-bold text-foreground">Multi-Format Extraction</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Extracts text page-by-page from PDFs, logically chunks DOCX documents, and preserves CSV tabular context.
              </p>
            </div>

            <div className="glass-panel-emerald p-6 rounded-xl space-y-4 hover:border-primary/30 transition-all duration-300">
              <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
                <Languages className="w-5 h-5" />
              </div>
              <h3 className="font-bold text-foreground">Multilingual Embeddings</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Automatically detects language. Performs vector indexing and handles queries across all whitelisted languages.
              </p>
            </div>

            <div className="glass-panel-emerald p-6 rounded-xl space-y-4 hover:border-primary/30 transition-all duration-300">
              <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
                <Cpu className="w-5 h-5" />
              </div>
              <h3 className="font-bold text-foreground">Local Llama 3 Grounding</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Fully integrates with Llama 3 running via local Ollama. Zero-leakage data privacy for enterprise projects.
              </p>
            </div>

            <div className="glass-panel-emerald p-6 rounded-xl space-y-4 hover:border-primary/30 transition-all duration-300">
              <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
                <ShieldAlert className="w-5 h-5" />
              </div>
              <h3 className="font-bold text-foreground">Out-of-Scope Shield</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Enforces a strict similarity score threshold (0.40) to block hallucinations and off-topic queries.
              </p>
            </div>

          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="w-full border-t border-border/20 py-8 z-10">
        <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row justify-between items-center gap-4 text-xs text-slate-500">
          <p>© 2026 AuraQA. Full-stack AI final-year project.</p>
          <div className="flex space-x-6">
            <span className="hover:text-primary transition-colors cursor-pointer">Privacy Policy</span>
            <span className="hover:text-primary transition-colors cursor-pointer">Terms of Service</span>
            <span className="hover:text-primary transition-colors cursor-pointer">API Documentation</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
