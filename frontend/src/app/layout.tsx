import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AuraQA | Multilingual Document AI Assistant",
  description: "Upload PDF, DOCX, TXT, or CSV files in English, French, Arabic, Spanish, German, or Hausa and converse with a local Llama 3 LLM. Safe, offline-compatible, and fully grounded in your data.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className="h-full antialiased"
    >
      <body className="min-h-full flex flex-col bg-background text-foreground">
        {children}
      </body>
    </html>
  );
}
