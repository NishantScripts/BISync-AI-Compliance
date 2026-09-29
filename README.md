# 🛡️ BISync — AI-Powered Intelligent Assistant & Compliance Auditor for Indian Standards

> **Team CodeX99 · SIH26107**  
> An enterprise-grade AI compliance copilot built for the Bureau of Indian Standards (BIS) to streamline product standard identification, audit lab reports, and detect counterfeit ISI marks.

---

## 🌟 Overview
The Bureau of Indian Standards publishes thousands of Indian Standards and manages complex certification schemes (such as CRS, FMCS, and Hallmarking). Navigating through massive documentation, manuals, and lists is time-consuming for MSMEs, startups, and consumers. 

**BISync** solves this through natural language processing, vector retrieval-augmented generation (RAG), and computer vision inspection, bridging the gap between consumers, industry auditors, and regulatory bodies.

---

## 🏗️ System Architecture & Tech Stack

BISync is engineered for **low-latency inference, zero-downtime resilience, and strict data grounding**:

- **Backend:** FastAPI (Python), Uvicorn, PyPDF2
- **AI Engine & Multi-Model Router:** Groq API leveraging `llama3-70b-8192` (for PDF analysis), `llama3-8b-8192` (for multilingual RAG chat), and Vision models (for counterfeit detection).
- **Vector Database:** ChromaDB (`bis_rulebook` collection) embedded with over 750+ simplified procedure standards and technical rule manuals[cite: 2].
- **Frontend:** Vite, React, TypeScript, Tailwind CSS, Lucide Icons.
- **Deployment & CI/CD:** Live production deployment on **Render** (Backend) and **Vercel** (Frontend).

---

## 🚀 Key Features

1. **AI Vision Inspector (`/scan-image`):**
   * Inspects product photos and packaging using Vision AI.
   * Detects missing or distorted ISI marks, invalid 7-digit CM/L license formats, and stamp font anomalies.
   * Generates confidence scores, forgery indicators, and role-specific summaries (Consumer plain-English vs. Auditor technical notes).

2. **Lab Report & Manual PDF Parser (`/parse-pdf`):**
   * Extracts raw text from uploaded lab test reports and BIS manuals using PyPDF2.
   * Sends text to LLaMA3-70B to return strict JSON compliance audits broken down by specific IS clauses, requirement criteria, and discrepancy flags.

3. **Multilingual BIS AI Chatbot (`/chat`):**
   * RAG-powered conversational assistant utilizing ChromaDB vector store.
   * Supports bilingual queries (English / Hindi) with conversational memory (session state handling).
   * Automatically cites applicable Indian Standard numbers (e.g., IS 4151, IS 15410[cite: 2]) for every response.

4. **Production Resilience (Multi-Model Smart Router & Fallbacks):**
   * Built-in load balancing across multiple API keys and models to bypass rate limits (`429 Too Many Requests`).
   * Graceful mock fallbacks ensuring the UI never crashes during high-stakes live demonstrations.

---

## 🛠️ Local Installation & Setup

### 1. Clone the Repository
```bash
git clone [https://github.com/NishantScripts/BISync-AI-Compliance.git](https://github.com/NishantScripts/BISync-AI-Compliance.git)
cd BISync-AI-Compliance
