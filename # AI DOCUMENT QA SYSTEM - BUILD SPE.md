# AI DOCUMENT QA SYSTEM - BUILD SPECIFICATION

You are a senior full-stack AI engineer.

Build a production-ready AI-powered Document Question Answering System.

## IMPORTANT RULES
- Do NOT generate everything at once.
- Work in modules step-by-step.
- Wait for confirmation after each module.
- Keep code clean, production-ready, and minimal.
- Avoid unnecessary explanations.
- Optimize for a final-year Computer Science project.

---

# PROJECT OVERVIEW

Build a system that:
1. Accepts  PDF
- DOCX
- TXT
- CSV
uploads
2. Extracts and processes text
3. Stores embeddings in a vector database
4. Answers questions ONLY from uploaded documents
5. Detects out-of-scope questions
6. Shows page/source references
7. Provides document summarization
8. Supports chat history

---

# TECH STACK (MANDATORY)

## Frontend
Next.js (App Router)
TypeScript
Tailwind CSS
Shadcn UI

## Backend
FastAPI (Python)

## Database
PostgreSQL

## Vector Database
FAISS

## Embeddings
sentence-transformers (all-MiniLM-L6-v2)

## File Storage
Local storage (uploads/ folder)

## LLM 
- Gemini API (preferred for simplicity) for online reque
- Llama 3 via Ollama (offline option)

---

# CORE FEATURES

## 1. Authentication
- Register
- Login
- JWT auth

## 2. Document Management
- Upload  PDF
- DOCX
- TXT
- CSV

- Store metadata in PostgreSQL
- Save file locally

## 3. Text Processing
- Extract text from PDF and DOCX
- Chunk text (500–1000 tokens)

## 4. Embeddings + Vector Store
- Convert chunks to embeddings
- Store in FAISS index
- Link embeddings to document_id

## 5. Question Answering (RAG)
Flow:
User Question → Embed → FAISS Search → Retrieve Top K → LLM Answer

Return:
- Answer
- Source page/chunk
- Confidence score

## 6. Out-of-Scope Detection
If similarity score < threshold (e.g. 0.75):
Return:
"This answer is not available in the uploaded document."

Then ask:
"Do you want me to search online?"

## 7. Document Summarization
- Full summary
- Key points
- Conclusions

## 8. Chat System
- Save conversations per document
- Retrieve chat history

---

# ONLINE SEARCH MODULE

If user requests external info:
- Use Gemini API OR free search API (Tavily/SerpAPI)
- Clearly label external answers

---

# BACKEND REQUIREMENTS

Build FastAPI backend with:

## Endpoints
- /auth/register
- /auth/login
- /upload
- /documents
- /chat
- /summarize
- /search 

## Services
- file_service
- rag_service
- embedding_service
- auth_service

---

# FRONTEND REQUIREMENTS

Build Next.js UI:

## Pages
- Landing page
- Dashboard
- Upload page
- Chat page
- Document viewer

## UI STYLE
- ChatGPT-like interface
- Sidebar for documents
- Clean SaaS design
- Dark and light mode support

---

# DATA MODELS (POSTGRESQL)

Users:
- id
- name
- email
- password_hash

Documents:
- id
- user_id
- filename
- filepath
- created_at

Chats:
- id
- document_id
- user_id

Messages:
- id
- chat_id
- role (user/assistant)
- content
- timestamp

---

# DEVELOPMENT PHASES

## Phase 1
- Backend setup
- Database setup
- Auth system

## Phase 2
- File upload system
- Text extraction

## Phase 3
- Embeddings + FAISS

## Phase 4
- RAG question answering

## Phase 5
- Frontend UI

## Phase 6
- Chat system + polishing

---

# OUTPUT FORMAT RULE

For every task:
1. Show folder structure (if needed)
2. Provide code only for the current module
3. Stop after module completion
4. Ask: "Proceed to next module?"

---

# GOAL

A fully functional AI document assistant that:
- Works like ChatGPT for uploaded PDFs
- Prevents hallucination
- Uses retrieval-based answers
- Looks like a modern SaaS product