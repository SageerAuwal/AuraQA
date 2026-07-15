"use client";

import React, { useEffect, useState, use } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "../../../services/api";
import { 
  ArrowLeft, Loader2, BookOpen, GraduationCap, 
  HelpCircle, Copy, Check, RotateCcw, AlertCircle, 
  ChevronLeft, ChevronRight, Globe, CheckCircle2, 
  Award, Sparkles, BookMarked, ListChecks, HelpCircle as QuestionIcon, Cpu, Sun, Moon
} from "lucide-react";

interface ChapterSummary {
  title: string;
  summary: string;
  start_page: number;
  end_page: number;
}

interface DocumentSummaryOut {
  id: number;
  document_id: number;
  summary_text: string;
  key_points: string[];
  conclusions: string;
  chapters: ChapterSummary[];
}

interface QuizQuestionOut {
  id: number;
  question_type: string; // 'mcq', 'tf', 'short'
  question_text: string;
  options: string[] | null;
  correct_answer: string;
  explanation: string | null;
}

interface QuizOut {
  id: number;
  document_id: number;
  created_at: string;
  questions: QuizQuestionOut[];
}

interface FlashcardOut {
  id: number;
  front: string;
  back: string;
}

interface FlashcardSetOut {
  id: number;
  document_id: number;
  created_at: string;
  cards: FlashcardOut[];
}

interface StudyPageProps {
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

export default function StudyClient({ params }: StudyPageProps) {
  const resolvedParams = use(params);
  const documentId = parseInt(resolvedParams.id, 10);

  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [generateStep, setGenerateStep] = useState("");
  const [error, setError] = useState("");
  const [activeModel, setActiveModel] = useState("qwen2.5:0.5b");
  const [theme, setTheme] = useState<"dark" | "light">("dark");

  useEffect(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("activeModel");
      if (saved) {
        setActiveModel(saved);
      } else {
        localStorage.setItem("activeModel", "qwen2.5:0.5b");
      }
      
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

  const handleModelChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const model = e.target.value;
    setActiveModel(model);
    if (typeof window !== "undefined") {
      localStorage.setItem("activeModel", model);
    }
  };
  
  // Dashboard Payload
  const [summary, setSummary] = useState<DocumentSummaryOut | null>(null);
  const [quiz, setQuiz] = useState<QuizOut | null>(null);
  const [flashcardSet, setFlashcardSet] = useState<FlashcardSetOut | null>(null);
  const [documentName, setDocumentName] = useState("Study Guide");

  // Tab controls
  const [activeTab, setActiveTab] = useState<"summary" | "quiz" | "flashcards">("summary");
  const [selectedChapterIdx, setSelectedChapterIdx] = useState<number>(0);

  // Flashcards state
  const [currentCardIdx, setCurrentCardIdx] = useState(0);
  const [isFlipped, setIsFlipped] = useState(false);

  // Quiz taking state
  const [quizAnswers, setQuizAnswers] = useState<Record<number, string>>({});
  const [quizSubmitted, setQuizSubmitted] = useState(false);
  const [quizScore, setQuizScore] = useState(0);

  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      router.push("/login");
      return;
    }
    fetchStudyData();
  }, [documentId]);

  const fetchStudyData = async () => {
    setLoading(true);
    setError("");
    try {
      // Fetch document details to show name
      const docs = await api.listDocuments();
      const currentDoc = docs.find((d: any) => d.id === documentId);
      if (currentDoc) {
        setDocumentName(currentDoc.filename);
      }

      // Fetch study dashboard materials
      const data = await api.getStudyDashboard(documentId);
      setSummary(data.summary);
      setQuiz(data.quiz);
      setFlashcardSet(data.flashcard_set);
      
      // Reset quiz responses if quiz is loaded
      if (data.quiz) {
        setQuizAnswers({});
        setQuizSubmitted(false);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load study dashboard payload.");
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateStudyMaterials = async (regenerate: any = false) => {
    const shouldRegenerate = typeof regenerate === "boolean" ? regenerate : false;
    setGenerating(true);
    setError("");
    try {
      setGenerateStep("Step 1/3: Analyzing chapters and writing summaries...");
      const sumRes = await api.generateSummary(documentId, shouldRegenerate);
      setSummary(sumRes);

      setGenerateStep("Step 2/3: Designing multiple choice, true/false, and short answer quizzes...");
      const quizRes = await api.generateQuiz(documentId);
      setQuiz(quizRes);

      setGenerateStep("Step 3/3: Drafting custom Q&A study flashcards...");
      const flashcardsRes = await api.generateFlashcards(documentId);
      setFlashcardSet(flashcardsRes);
      
      setQuizAnswers({});
      setQuizSubmitted(false);
    } catch (err: any) {
      setError(err.message || "Failed to generate study materials. Please try again.");
    } finally {
      setGenerating(false);
      setGenerateStep("");
    }
  };

  const handleOptionSelect = (questionId: number, option: string) => {
    if (quizSubmitted) return;
    setQuizAnswers(prev => ({ ...prev, [questionId]: option }));
  };

  const handleShortAnswerChange = (questionId: number, text: string) => {
    if (quizSubmitted) return;
    setQuizAnswers(prev => ({ ...prev, [questionId]: text }));
  };

  const handleSubmitQuiz = () => {
    if (!quiz || quizSubmitted) return;
    
    let score = 0;
    quiz.questions.forEach(q => {
      const userAnswer = (quizAnswers[q.id] || "").trim().toLowerCase();
      const correctAnswer = q.correct_answer.trim().toLowerCase();
      
      if (q.question_type === "short") {
        // Simple substring check for short answer evaluation to make it flexible
        if (correctAnswer && userAnswer.includes(correctAnswer)) {
          score += 1;
        }
      } else {
        if (userAnswer === correctAnswer) {
          score += 1;
        }
      }
    });

    setQuizScore(score);
    setQuizSubmitted(true);
  };

  const handleResetQuiz = () => {
    setQuizAnswers({});
    setQuizSubmitted(false);
    setQuizScore(0);
  };

  // Helper to format ISO code to Full Name
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

  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground selection:bg-primary selection:text-background">
      
      {/* 3D Flashcard Flip CSS Styles injected locally */}
      <style jsx global>{`
        .perspective-1000 {
          perspective: 1000px;
        }
        .transform-style-3d {
          transform-style: preserve-3d;
        }
        .backface-hidden {
          backface-visibility: hidden;
        }
        .rotate-y-180 {
          transform: rotateY(180deg);
        }
      `}</style>

      {/* Header Bar */}
      <header className="w-full border-b border-border/10 bg-slate-950/40 backdrop-blur-md sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <button
              onClick={() => router.push("/dashboard")}
              className="flex items-center justify-center p-2 rounded-lg border border-border/30 hover:border-primary/40 hover:bg-primary/5 text-slate-300 hover:text-primary transition-all duration-200 cursor-pointer"
            >
              <ArrowLeft className="w-4 h-4" />
            </button>
            <div className="flex items-center space-x-3">
              <div className="w-9 h-9 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center text-primary">
                <GraduationCap className="w-5 h-5" />
              </div>
              <div>
                <h1 className="font-bold text-sm text-foreground max-w-xs sm:max-w-md truncate" title={documentName}>
                  {documentName}
                </h1>
                <p className="text-[10px] text-slate-400">Study Mode Dashboard</p>
              </div>
            </div>
          </div>
          
          <div className="flex items-center space-x-3">
            <button 
              onClick={toggleTheme}
              className="p-2 rounded-lg border border-border/30 hover:border-primary/40 hover:bg-primary/5 text-slate-400 hover:text-primary transition-all duration-200 cursor-pointer animate-fade-in"
              title={theme === "dark" ? "Switch to Light Mode" : "Switch to Dark Mode"}
            >
              {theme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>

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
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-grow max-w-7xl w-full mx-auto px-6 py-8 flex flex-col space-y-6">
        
        {/* Error Notification */}
        {error && (
          <div className="p-4 rounded-xl bg-red-950/30 border border-red-900/40 text-red-200 text-sm flex items-start space-x-3">
            <AlertCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {loading ? (
          <div className="flex-grow flex flex-col justify-center items-center py-24 space-y-3">
            <Loader2 className="w-12 h-12 text-primary animate-spin" />
            <span className="text-sm text-slate-400">Loading your study environment...</span>
          </div>
        ) : generating ? (
          <div className="flex-grow flex flex-col justify-center items-center py-20 space-y-6 max-w-md mx-auto text-center">
            <Loader2 className="w-16 h-16 text-primary animate-spin" />
            <div className="space-y-2">
              <h3 className="text-lg font-bold text-primary">Generating Study Materials</h3>
              <p className="text-xs text-slate-400 animate-pulse">{generateStep}</p>
            </div>
            <div className="w-full bg-slate-900 h-1.5 rounded-full overflow-hidden">
              <div 
                className={`bg-primary h-full transition-all duration-500 ${
                  generateStep.includes("Step 1") ? "w-1/3" : generateStep.includes("Step 2") ? "w-2/3" : "w-11/12"
                }`}
              />
            </div>
            <p className="text-[10px] text-slate-500 leading-normal">
              Our service runs automated chapter extraction, summarizes paragraphs segment-by-segment, and builds custom question matrices with explanations. This may take 30-45 seconds.
            </p>
          </div>
        ) : !summary ? (
          /* Empty State - Trigger Generation */
          <div className="flex-grow flex flex-col justify-center items-center text-center max-w-lg mx-auto py-16 space-y-8">
            <div className="w-20 h-20 rounded-2xl bg-primary/5 border border-primary/15 flex items-center justify-center text-primary shadow-lg shadow-primary/5">
              <GraduationCap className="w-10 h-10" />
            </div>
            <div className="space-y-3">
              <h2 className="text-2xl font-bold tracking-tight">Prepare your Study Guide</h2>
              <p className="text-sm text-slate-400 leading-relaxed">
                Generate study aids to analyze chapters, summarize critical details, and test yourself with custom Q&A quizzes and flashcards grounded directly in the document.
              </p>
            </div>
            <button
              onClick={() => handleGenerateStudyMaterials(false)}
              className="px-6 py-3 rounded-lg bg-primary hover:bg-primary-hover text-background font-bold transition-all duration-200 shadow-md shadow-primary/10 flex items-center space-x-2 cursor-pointer"
            >
              <Sparkles className="w-4 h-4" />
              <span>Generate Study Materials</span>
            </button>
          </div>
        ) : (
          /* Active Study dashboard panels */
          <div className="space-y-6 flex-grow flex flex-col">
            
            {/* Tabs Selector & Action Bar */}
            <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4 border-b border-border/15 pb-1">
              <div className="flex border-b border-transparent max-w-md flex-grow">
                <button
                  onClick={() => setActiveTab("summary")}
                  className={`flex-grow py-3 text-center border-b-2 font-bold text-xs uppercase tracking-wider transition-all cursor-pointer flex items-center justify-center space-x-1.5 ${
                    activeTab === "summary" 
                      ? "border-primary text-primary" 
                      : "border-transparent text-slate-400 hover:text-slate-200"
                  }`}
                >
                  <BookMarked className="w-4 h-4" />
                  <span>Chapter Summaries</span>
                </button>
                
                <button
                  onClick={() => setActiveTab("quiz")}
                  className={`flex-grow py-3 text-center border-b-2 font-bold text-xs uppercase tracking-wider transition-all cursor-pointer flex items-center justify-center space-x-1.5 ${
                    activeTab === "quiz" 
                      ? "border-primary text-primary" 
                      : "border-transparent text-slate-400 hover:text-slate-200"
                  }`}
                >
                  <ListChecks className="w-4 h-4" />
                  <span>Interactive Quiz</span>
                </button>
                
                <button
                  onClick={() => setActiveTab("flashcards")}
                  className={`flex-grow py-3 text-center border-b-2 font-bold text-xs uppercase tracking-wider transition-all cursor-pointer flex items-center justify-center space-x-1.5 ${
                    activeTab === "flashcards" 
                      ? "border-primary text-primary" 
                      : "border-transparent text-slate-400 hover:text-slate-200"
                  }`}
                >
                  <HelpCircle className="w-4 h-4" />
                  <span>Q&A Flashcards</span>
                </button>
              </div>

              <button
                onClick={() => {
                  if (confirm("Are you sure you want to regenerate all study materials? This will replace your current summary, quiz questions, and flashcards.")) {
                    handleGenerateStudyMaterials(true);
                  }
                }}
                className="flex items-center space-x-1.5 px-3 py-1.5 rounded bg-primary/10 border border-primary/30 hover:border-primary/50 text-primary hover:text-primary-hover text-[10px] font-bold transition-all duration-150 cursor-pointer mb-2 sm:mb-0"
              >
                <RotateCcw className="w-3 h-3" />
                <span>Regenerate Study Guide</span>
              </button>
            </div>

            {/* TAB CONTENTS */}
            <div className="flex-grow">
              
              {/* 1. SUMMARY TAB */}
              {activeTab === "summary" && (
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
                  
                  {/* Left Column: Detected Chapters */}
                  <div className="lg:col-span-4 space-y-4">
                    <div className="p-5 rounded-xl border border-border/10 bg-slate-950/20 space-y-3">
                      <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center space-x-1.5">
                        <BookOpen className="w-4 h-4 text-primary" />
                        <span>Auto-Detected Chapters</span>
                      </h3>
                      
                      <div className="space-y-2 max-h-[400px] overflow-y-auto pr-1">
                        {summary.chapters.map((ch, idx) => (
                          <button
                            key={idx}
                            onClick={() => setSelectedChapterIdx(idx)}
                            className={`w-full text-left p-3 rounded-lg border text-xs transition-all cursor-pointer ${
                              selectedChapterIdx === idx
                                ? "bg-primary/5 border-primary/40 text-primary font-bold"
                                : "bg-transparent border-border/20 text-slate-300 hover:bg-slate-900/40"
                            }`}
                          >
                            <div className="flex justify-between items-center mb-1">
                              <span className="truncate max-w-[80%]">{ch.title}</span>
                              <span className="text-[9px] font-normal text-slate-500 shrink-0">
                                Pages {ch.start_page}–{ch.end_page}
                              </span>
                            </div>
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Right Column: Summaries Details */}
                  <div className="lg:col-span-8 space-y-6">
                    {/* Chapter Summary Box */}
                    <div className="glass-panel-emerald p-6 rounded-xl space-y-3 relative overflow-hidden">
                      <div className="absolute top-0 right-0 w-24 h-24 bg-primary/5 rounded-full blur-2xl pointer-events-none" />
                      <div className="flex items-center justify-between pb-2 border-b border-border/10">
                        <h4 className="font-bold text-foreground text-base">
                          {summary.chapters[selectedChapterIdx]?.title || "Chapter Details"}
                        </h4>
                        <span className="px-2 py-0.5 rounded bg-primary/10 border border-primary/20 text-[9px] font-bold text-primary uppercase">
                          Pages {summary.chapters[selectedChapterIdx]?.start_page}–{summary.chapters[selectedChapterIdx]?.end_page}
                        </span>
                      </div>
                      <p className="text-xs text-slate-300 leading-relaxed whitespace-pre-line">
                        {formatTextWithBold(summary.chapters[selectedChapterIdx]?.summary || "No summary details generated.")}
                      </p>
                    </div>

                    {/* Full Summary Box */}
                    <div className="glass-panel p-6 rounded-xl space-y-4">
                      <h4 className="font-bold text-foreground text-sm flex items-center space-x-1.5 pb-2 border-b border-border/10">
                        <BookMarked className="w-4 h-4 text-primary" />
                        <span>Comprehensive Document Summary</span>
                      </h4>
                      <p className="text-xs text-slate-300 leading-relaxed whitespace-pre-line">
                        {formatTextWithBold(summary.summary_text)}
                      </p>
                    </div>

                    {/* Grid of Key Concepts & Conclusion */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      
                      {/* Key Concepts Box */}
                      <div className="glass-panel p-6 rounded-xl space-y-4">
                        <h4 className="font-bold text-foreground text-sm flex items-center space-x-1.5 pb-2 border-b border-border/10">
                          <ListChecks className="w-4 h-4 text-primary" />
                          <span>Key Concepts</span>
                        </h4>
                        <ul className="space-y-2.5">
                          {summary.key_points.map((pt, idx) => (
                            <li key={idx} className="flex items-start space-x-2.5 text-xs text-slate-300 leading-relaxed">
                              <CheckCircle2 className="w-4 h-4 text-primary shrink-0 mt-0.5" />
                              <span>{formatTextWithBold(pt)}</span>
                            </li>
                          ))}
                        </ul>
                      </div>

                      {/* Conclusions Box */}
                      <div className="glass-panel p-6 rounded-xl space-y-4">
                        <h4 className="font-bold text-foreground text-sm flex items-center space-x-1.5 pb-2 border-b border-border/10">
                          <Award className="w-4 h-4 text-primary" />
                          <span>Study Conclusions</span>
                        </h4>
                        <p className="text-xs text-slate-300 leading-relaxed whitespace-pre-line">
                          {formatTextWithBold(summary.conclusions)}
                        </p>
                      </div>

                    </div>
                  </div>

                </div>
              )}

              {/* 2. QUIZ TAB */}
              {activeTab === "quiz" && (
                <div className="max-w-3xl mx-auto space-y-8">
                  {/* Generate Quiz Prompt if none exists */}
                  {!quiz ? (
                    <div className="glass-panel p-8 rounded-xl text-center space-y-6">
                      <QuestionIcon className="w-12 h-12 text-slate-500 mx-auto" />
                      <div className="space-y-2">
                        <h3 className="font-bold text-base">Quiz not generated yet</h3>
                        <p className="text-xs text-slate-400 max-w-sm mx-auto">
                          Create an interactive assessment containing MCQ, True/False, and Short Answer questions to test your knowledge.
                        </p>
                      </div>
                      <button
                        onClick={() => handleGenerateStudyMaterials(false)}
                        className="px-5 py-2.5 rounded bg-primary hover:bg-primary-hover text-background text-xs font-bold transition-all duration-150 cursor-pointer"
                      >
                        Generate Assessment
                      </button>
                    </div>
                  ) : (
                    <div className="space-y-6">
                      {/* Scoreboard panel on quiz submit */}
                      {quizSubmitted && (
                        <div className="glass-panel-emerald p-6 rounded-xl flex items-center justify-between">
                          <div className="space-y-1">
                            <h3 className="font-bold text-lg text-primary flex items-center space-x-2">
                              <Award className="w-5 h-5" />
                              <span>Quiz Assessment Graded</span>
                            </h3>
                            <p className="text-xs text-slate-400">
                              You answered {quizScore} out of {quiz.questions.length} questions correctly.
                            </p>
                          </div>
                          <div className="text-right">
                            <span className="text-3xl font-extrabold text-primary">
                              {((quizScore / quiz.questions.length) * 100).toFixed(0)}%
                            </span>
                            <p className="text-[10px] text-slate-500 mt-1">
                              ({quizScore}/{quiz.questions.length} correct)
                            </p>
                          </div>
                        </div>
                      )}

                      {/* Quiz list */}
                      <div className="space-y-6">
                        {quiz.questions.map((q, idx) => {
                          const isCorrect = quizSubmitted && (
                            q.question_type === "short"
                              ? (quizAnswers[q.id] || "").trim().toLowerCase().includes(q.correct_answer.trim().toLowerCase())
                              : (quizAnswers[q.id] || "").trim().toLowerCase() === q.correct_answer.trim().toLowerCase()
                          );
                          const isAnswered = !!(quizAnswers[q.id] || "").trim();

                          return (
                            <div 
                              key={q.id}
                              className={`glass-panel p-6 rounded-xl border transition-all duration-200 ${
                                quizSubmitted 
                                  ? isCorrect 
                                    ? "border-emerald-500/40 bg-emerald-950/5" 
                                    : "border-red-500/40 bg-red-950/5"
                                  : "border-border/10"
                              }`}
                            >
                              <div className="flex items-start space-x-3 mb-4">
                                <span className="w-6 h-6 rounded bg-slate-900 border border-border/30 flex items-center justify-center text-xs font-bold text-slate-400 shrink-0">
                                  {idx + 1}
                                </span>
                                <div>
                                  <span className="px-2 py-0.5 rounded bg-slate-800 text-[9px] font-bold text-slate-400 uppercase tracking-wider mb-2 inline-block">
                                    {q.question_type === "mcq" ? "Multiple Choice" : q.question_type === "tf" ? "True / False" : "Short Answer"}
                                  </span>
                                  <h4 className="font-bold text-sm text-foreground leading-relaxed">
                                    {formatTextWithBold(q.question_text)}
                                  </h4>
                                </div>
                              </div>

                              {/* MCQ Options Rendering */}
                              {q.question_type === "mcq" && q.options && (
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pl-9">
                                  {q.options.map((opt) => {
                                    const optionLetter = opt.trim().substring(0, 1).toUpperCase(); // Extract A, B, C, D
                                    const isSelected = quizAnswers[q.id] === optionLetter;
                                    const isCorrectOpt = q.correct_answer === optionLetter;

                                    return (
                                      <button
                                        key={opt}
                                        type="button"
                                        disabled={quizSubmitted}
                                        onClick={() => handleOptionSelect(q.id, optionLetter)}
                                        className={`w-full text-left p-3 rounded-lg border text-xs transition-all cursor-pointer ${
                                          quizSubmitted
                                            ? isCorrectOpt
                                              ? "bg-emerald-950/40 border-emerald-500/40 text-emerald-200 font-bold"
                                              : isSelected
                                                ? "bg-red-950/40 border-red-500/40 text-red-200"
                                                : "bg-slate-950/20 border-border/10 text-slate-500"
                                            : isSelected
                                              ? "bg-primary/10 border-primary/50 text-primary font-bold"
                                              : "bg-slate-950/10 border-border/10 text-slate-300 hover:bg-slate-900/30"
                                        }`}
                                      >
                                        {opt}
                                      </button>
                                    );
                                  })}
                                </div>
                              )}

                              {/* True / False Options Rendering */}
                              {q.question_type === "tf" && (
                                <div className="flex space-x-4 pl-9">
                                  {["True", "False"].map((opt) => {
                                    const isSelected = quizAnswers[q.id] === opt;
                                    const isCorrectOpt = q.correct_answer === opt;

                                    return (
                                      <button
                                        key={opt}
                                        type="button"
                                        disabled={quizSubmitted}
                                        onClick={() => handleOptionSelect(q.id, opt)}
                                        className={`px-5 py-2.5 rounded-lg border text-xs transition-all cursor-pointer ${
                                          quizSubmitted
                                            ? isCorrectOpt
                                              ? "bg-emerald-950/40 border-emerald-500/40 text-emerald-200 font-bold"
                                              : isSelected
                                                ? "bg-red-950/40 border-red-500/40 text-red-200"
                                                : "bg-slate-950/20 border-border/10 text-slate-500"
                                            : isSelected
                                              ? "bg-primary/10 border-primary/50 text-primary font-bold"
                                              : "bg-slate-950/10 border-border/10 text-slate-300 hover:bg-slate-900/30"
                                        }`}
                                      >
                                        {opt}
                                      </button>
                                    );
                                  })}
                                </div>
                              )}

                              {/* Short Answer Input Rendering */}
                              {q.question_type === "short" && (
                                <div className="pl-9 space-y-2">
                                  <input
                                    type="text"
                                    disabled={quizSubmitted}
                                    placeholder={quizSubmitted ? "No answer provided" : "Type your concise answer here..."}
                                    value={quizAnswers[q.id] || ""}
                                    onChange={(e) => handleShortAnswerChange(q.id, e.target.value)}
                                    className={`w-full max-w-md bg-slate-950/40 border rounded-lg px-4 py-2 text-xs focus:outline-none focus:border-primary/50 text-foreground transition-all duration-150 disabled:opacity-75 ${
                                      quizSubmitted
                                        ? isCorrect
                                          ? "border-emerald-500/40 text-emerald-200"
                                          : "border-red-500/40 text-red-200"
                                        : "border-border/30"
                                    }`}
                                  />
                                  {quizSubmitted && !isCorrect && (
                                    <p className="text-[10px] text-emerald-400 font-semibold">
                                      Correct answer keyword: <span className="underline">{q.correct_answer}</span>
                                    </p>
                                  )}
                                </div>
                              )}

                              {/* Quiz explanation box on submit */}
                              {quizSubmitted && q.explanation && (
                                <div className="mt-4 pt-3 border-t border-border/10 pl-9 text-xs text-slate-400 leading-relaxed">
                                  <span className="font-bold text-[10px] text-slate-300 uppercase tracking-wider block mb-1">
                                    Explanation:
                                  </span>
                                  {formatTextWithBold(q.explanation)}
                                </div>
                              )}

                            </div>
                          );
                        })}
                      </div>

                      {/* Footer Actions */}
                      <div className="flex justify-end space-x-4 pt-4">
                        {quizSubmitted ? (
                          <button
                            onClick={handleResetQuiz}
                            className="flex items-center space-x-1.5 px-4 py-2.5 rounded border border-border/30 hover:border-primary/40 text-xs font-bold transition-all duration-150 cursor-pointer"
                          >
                            <RotateCcw className="w-3.5 h-3.5" />
                            <span>Retake Quiz</span>
                          </button>
                        ) : (
                          <button
                            onClick={handleSubmitQuiz}
                            className="px-5 py-2.5 rounded bg-primary hover:bg-primary-hover text-background text-xs font-bold transition-all duration-150 cursor-pointer shadow-md shadow-primary/10"
                          >
                            Submit and Grade Quiz
                          </button>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* 3. FLASHCARDS TAB */}
              {activeTab === "flashcards" && (
                <div className="max-w-xl mx-auto space-y-8 flex flex-col justify-center items-center py-6">
                  {!flashcardSet ? (
                    <div className="glass-panel p-8 rounded-xl text-center space-y-6 w-full">
                      <BookMarked className="w-12 h-12 text-slate-500 mx-auto" />
                      <div className="space-y-2">
                        <h3 className="font-bold text-base">Flashcards not generated</h3>
                        <p className="text-xs text-slate-400 max-w-sm mx-auto">
                          Create concise double-sided question and answer cards to review key concepts.
                        </p>
                      </div>
                      <button
                        onClick={() => handleGenerateStudyMaterials(false)}
                        className="px-5 py-2.5 rounded bg-primary hover:bg-primary-hover text-background text-xs font-bold transition-all duration-150 cursor-pointer"
                      >
                        Generate Flashcards
                      </button>
                    </div>
                  ) : (
                    <div className="w-full flex flex-col items-center space-y-8">
                      {/* Progress bar */}
                      <div className="w-full space-y-1">
                        <div className="flex justify-between text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                          <span>Progress</span>
                          <span>Card {currentCardIdx + 1} of {flashcardSet.cards.length}</span>
                        </div>
                        <div className="w-full h-1 bg-slate-900 rounded-full overflow-hidden">
                          <div 
                            className="bg-primary h-full transition-all duration-300"
                            style={{ width: `${((currentCardIdx + 1) / flashcardSet.cards.length) * 100}%` }}
                          />
                        </div>
                      </div>

                      {/* 3D Flipping Card Body Container */}
                      <div 
                        onClick={() => setIsFlipped(prev => !prev)}
                        className="w-full h-72 perspective-1000 cursor-pointer group"
                      >
                        <div className={`relative w-full h-full duration-500 transform-style-3d ${
                          isFlipped ? "rotate-y-180" : ""
                        }`}>
                          
                          {/* Front Side: Question */}
                          <div className="absolute w-full h-full backface-hidden glass-panel-emerald p-8 rounded-2xl flex flex-col justify-between items-center text-center select-none shadow-xl hover:border-primary/30 transition-all">
                            <span className="px-2 py-0.5 rounded bg-primary/10 border border-primary/20 text-[9px] font-bold text-primary tracking-wider uppercase">
                              Question / Concept
                            </span>
                            <h3 className="font-extrabold text-foreground text-base max-w-md leading-relaxed whitespace-pre-line">
                              {formatTextWithBold(flashcardSet.cards[currentCardIdx]?.front)}
                            </h3>
                            <span className="text-[10px] text-slate-500 font-medium">
                              Click card to reveal answer
                            </span>
                          </div>

                          {/* Back Side: Answer */}
                          <div className="absolute w-full h-full backface-hidden rotate-y-180 bg-slate-900 border border-primary/30 p-8 rounded-2xl flex flex-col justify-between items-center text-center select-none shadow-xl">
                            <span className="px-2 py-0.5 rounded bg-emerald-950 border border-emerald-500/30 text-[9px] font-bold text-emerald-400 tracking-wider uppercase">
                              Correct Explanation / Answer
                            </span>
                            <p className="text-slate-200 text-xs leading-relaxed max-w-md whitespace-pre-line">
                              {formatTextWithBold(flashcardSet.cards[currentCardIdx]?.back)}
                            </p>
                            <span className="text-[10px] text-slate-500 font-medium">
                              Click card to show question
                            </span>
                          </div>

                        </div>
                      </div>

                      {/* Flip Actions and navigations */}
                      <div className="flex items-center space-x-6">
                        <button
                          type="button"
                          disabled={currentCardIdx === 0}
                          onClick={() => {
                            setIsFlipped(false);
                            setTimeout(() => setCurrentCardIdx(prev => prev - 1), 150);
                          }}
                          className="flex items-center justify-center p-2 rounded-lg border border-border/30 hover:border-primary/40 text-slate-300 hover:text-primary transition-all disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
                        >
                          <ChevronLeft className="w-5 h-5" />
                        </button>

                        <button
                          type="button"
                          onClick={() => setIsFlipped(prev => !prev)}
                          className="px-5 py-2.5 rounded-lg border border-primary/25 hover:border-primary/50 bg-primary/5 hover:bg-primary/10 text-primary text-xs font-bold transition-all cursor-pointer"
                        >
                          Flip Card
                        </button>

                        <button
                          type="button"
                          disabled={currentCardIdx === flashcardSet.cards.length - 1}
                          onClick={() => {
                            setIsFlipped(false);
                            setTimeout(() => setCurrentCardIdx(prev => prev + 1), 150);
                          }}
                          className="flex items-center justify-center p-2 rounded-lg border border-border/30 hover:border-primary/40 text-slate-300 hover:text-primary transition-all disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
                        >
                          <ChevronRight className="w-5 h-5" />
                        </button>
                      </div>

                    </div>
                  )}
                </div>
              )}

            </div>

          </div>
        )}

      </main>
    </div>
  );
}
