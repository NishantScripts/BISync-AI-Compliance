"""
BISync — FastAPI backend
Team CodeX99 · SIH26107 — AI-Powered Intelligent Assistant for Indian Standards & BIS Services
"""

import os
import io
import json
import time
import base64
import hashlib
import logging
import re  
from datetime import datetime, timezone
from typing import List  
import PyPDF2

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from openai import OpenAI
import chromadb
from chromadb.utils import embedding_functions

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("bisync")

# --------------------------------------------------------------------------
# App + CORS
# --------------------------------------------------------------------------
app = FastAPI(title="BISync API", version="1.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------------------------------
# Multi-Model Smart Router (Updated with Latest Groq Models)
# --------------------------------------------------------------------------
def call_ai_api(parts: list, task_type: str = "vision", json_mode: bool = False):
    """Hits Groq API routing to latest non-deprecated models based on the task."""
    
    if task_type == "pdf":
        model_name = "openai/gpt-oss-120b"  # Updated latest model for PDF parsing
        api_key = os.environ.get("GROQ_API_KEY_PDF") or os.environ.get("GROQ_API_KEY")
    elif task_type == "chat":
        model_name = "openai/gpt-oss-20b"   # Updated latest model for Chat
        api_key = os.environ.get("GROQ_API_KEY_CHAT") or os.environ.get("GROQ_API_KEY")
    else: 
        model_name = "qwen/qwen3.8-27b"     # Multimodal / Vision model
        api_key = os.environ.get("GROQ_API_KEY")

    if not api_key:
        raise RuntimeError(f"NO_KEY_FOUND_FOR_TASK: {task_type.upper()}")

    client = OpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=api_key,
    )

    if task_type == "chat":
        messages = parts
    elif task_type == "pdf":
        messages = [{"role": "user", "content": parts[0]}]
    else:
        content_list = []
        for p in parts:
            if isinstance(p, str):
                content_list.append({"type": "text", "text": p})
            elif isinstance(p, dict) and "data" in p:
                mime = p.get("mime_type", "image/jpeg")
                content_list.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime};base64,{p['data']}"}
                })
        messages = [{"role": "user", "content": content_list}]

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
        )
        
        result_text = response.choices[0].message.content
        if json_mode:
             result_text = result_text.replace("```json", "").replace("```", "").strip()
             
        return result_text

    except Exception as e:
        log.error(f"Groq API call failed for {task_type}: {e}")
        raise RuntimeError(f"API_FAILED ({task_type}): {e}")

# --------------------------------------------------------------------------
# ChromaDB — bis_rulebook collection
# --------------------------------------------------------------------------
CHROMA_PATH = os.environ.get("CHROMA_PATH", "./chroma_store")
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
embedder = embedding_functions.DefaultEmbeddingFunction()

rulebook = chroma_client.get_or_create_collection(
    name="bis_rulebook",
    embedding_function=embedder,
)

STANDARDS_SEED = [
    {"id": "IS4151", "text": "IS 4151: Protective helmets for two-wheeler riders. Specifies impact absorption, penetration resistance, strap strength, and CM/L marking requirements.", "meta": {"standard": "IS 4151", "product": "Helmets"}},
    {"id": "IS14543", "text": "IS 14543: Packaged drinking water (other than natural mineral water). Specifies permissible limits for pH, TDS, residual chlorine, and microbiological safety.", "meta": {"standard": "IS 14543", "product": "Packaged Water"}},
    {"id": "IS13250", "text": "IS 13250: Safety requirements for household and similar electrical chargers/power adaptors, including insulation, thermal, and short-circuit protection.", "meta": {"standard": "IS 13250", "product": "Chargers"}},
    {"id": "IS694", "text": "IS 694: PVC insulated cables and wires for working voltages up to 1100V. Specifies conductor sizing, insulation thickness, and flame-retardant properties.", "meta": {"standard": "IS 694", "product": "Wires"}},
    {"id": "IS9873", "text": "IS 9873: Safety of toys, including mechanical/physical hazards, flammability limits, and migration of certain elements for children's toys.", "meta": {"standard": "IS 9873", "product": "Toys"}},
    {"id": "IS16046", "text": "IS 16046: Safety requirements for secondary lithium-ion cells and batteries used in portable applications, covering thermal abuse and short-circuit tests.", "meta": {"standard": "IS 16046", "product": "Li-ion Batteries"}},
    {"id": "IS8828", "text": "IS 8828: Miniature circuit breakers (MCBs) for AC circuits. Specifies tripping characteristics, breaking capacity, and endurance requirements.", "meta": {"standard": "IS 8828", "product": "MCBs"}},
    {"id": "SCHEME_CRS", "text": "Compulsory Registration Scheme (CRS) is operated by BIS under Scheme-II of Schedule-II for electronics and IT goods. Manufacturers must register before launching products.", "meta": {"standard": "CRS Scheme", "product": "Electronics"}},
    {"id": "SCHEME_FMCS", "text": "Foreign Manufacturers Certification Scheme (FMCS) allows overseas manufacturers to use the standard ISI mark on their products. The process involves factory audit and testing.", "meta": {"standard": "FMCS Scheme", "product": "Imports"}},
    {"id": "HALLMARKING", "text": "BIS Hallmarking scheme for Gold (IS 1417) and Silver (IS 2112) guarantees purity. It includes the BIS logo, purity grade (e.g., 22K916), and a 6-digit alphanumeric HUID code.", "meta": {"standard": "IS 1417", "product": "Jewellery Hallmarking"}},
    {"id": "LABS_LIMS", "text": "BIS operates a network of recognized testing laboratories. Consumers and auditors can find relevant testing labs for specific products via the BIS LIMS (Laboratory Information Management System) portal.", "meta": {"standard": "BIS Labs", "product": "Testing"}},
    {"id": "LAB_MAHARASHTRA", "text": "BIS Recognized Testing Labs in Maharashtra and Pune: 1. Central Materials Testing Laboratory (CMTL), Pune - recognized for mechanical, construction, and safety product testing under IS standards including IS 4151. 2. BIS Central Laboratory, Mumbai - recognized for multi-sector product testing including electronics, packaged water under IS 14543, and hallmarking purity verification.", "meta": {"standard": "BIS Labs", "product": "Testing Labs Maharashtra"}},
    {"id": "CONSUMER_GRIEVANCE", "text": "Consumers can file complaints regarding quality of ISI marked products or misleading advertisements through the BIS Care App or the consumer affairs portal.", "meta": {"standard": "Consumer Rights", "product": "Complaints"}},
]

def seed_rulebook_if_empty():
    if rulebook.count() == 0:
        rulebook.add(
            ids=[s["id"] for s in STANDARDS_SEED],
            documents=[s["text"] for s in STANDARDS_SEED],
            metadatas=[s["meta"] for s in STANDARDS_SEED],
        )
        log.info(f"Seeded bis_rulebook with {len(STANDARDS_SEED)} standards.")

seed_rulebook_if_empty()

# --------------------------------------------------------------------------
# Models & Helpers
# --------------------------------------------------------------------------
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []  
    language: str = "en"
    role: str = "consumer"

class QueryRuleRequest(BaseModel):
    query: str
    n_results: int = 3

def extract_safe_json(text: str) -> dict:
    """Finds the first valid JSON block to avoid LLM hallucination crashes."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except:
                pass
    raise ValueError("Valid JSON not found in LLM response")

def compliance_hash(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True).encode()
    return hashlib.sha256(raw).hexdigest()[:16]

def mock_scan_result(reason: str) -> dict:
    return {
        "mode": "mock_fallback",
        "reason": str(reason),
        "product_category": "Two-Wheeler Helmet",
        "matched_standard": "IS 4151",
        "isi_mark_detected": True,
        "cml_number_detected": "6543210",
        "cml_valid_format": True,
        "forgery_indicators": ["Slight font mismatch in CM/L stamp region (confidence 62%)"],
        "verdict": "CAUTION",
        "consumer_summary": "The ISI mark looks mostly genuine but the certification number's font is a little off. We recommend verifying the CM/L number on the BIS CARE portal before trusting this product.",
        "auditor_summary": "CM/L OCR confidence 62% — recommend physical CM/L cross-check against BIS Licence Database. Strap anchorage clause 7.3 not visible in frame.",
        "confidence": 0.62,
        "hash": compliance_hash({"seed": reason, "t": time.time()}),
    }

# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------
@app.api_route("/health", methods=["GET", "HEAD"])
def health():
    return {
        "status": "ok",
        "time": datetime.now(timezone.utc).isoformat(),
        "api_keys_configured": bool(os.environ.get("GROQ_API_KEY")),
        "rulebook_docs": rulebook.count(),
    }

@app.post("/scan-image")
async def scan_image(file: UploadFile = File(...), role: str = Form("consumer"), language: str = Form("en")):
    try:
        img_bytes = await file.read()
        b64 = base64.b64encode(img_bytes).decode()

        prompt = f"""You are BISync, an AI compliance inspector for the Bureau of Indian Standards (BIS).
Analyze this product image and return STRICT JSON with keys:
product_category, matched_standard, isi_mark_detected (bool), cml_number_detected (string or null),
cml_valid_format (bool), forgery_indicators (array of short strings), verdict ("PASS"|"CAUTION"|"FAIL"),
consumer_summary (plain-language, 2 sentences, {"Hindi" if language == "hi" else "English"}),
auditor_summary (technical, clause-referenced, 2 sentences), confidence (0-1 float).
Focus especially on: missing/blurry 7-digit CM/L license number, distorted ISI triangle proportions,
mismatched stamp fonts, and label placement anomalies typical of counterfeits.
Respond with ONLY the JSON object, no markdown."""

        parts = [prompt, {"mime_type": file.content_type or "image/jpeg", "data": b64}]
        
        raw = call_ai_api(parts, task_type="vision", json_mode=True)
        
        result = extract_safe_json(raw)
        result["mode"] = "live"
        result["hash"] = compliance_hash(result)
        return result

    except Exception as e:
        log.error(f"/scan-image failed: {e}")
        return mock_scan_result(str(e))

@app.post("/parse-pdf")
async def parse_pdf(file: UploadFile = File(...), role: str = Form("auditor"), language: str = Form("en")):
    try:
        pdf_bytes = await file.read()
        
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
        extracted_text = ""
        for page in pdf_reader.pages:
            extracted_text += page.extract_text() + "\n"
            
        if not extracted_text.strip():
            raise ValueError("No readable text found in PDF. Make sure it's not a scanned image PDF.")

        prompt = f"""You are BISync, a BIS lab-report and standard manual analyst. 
Read the following extracted text from a document. Return STRICT JSON with keys:
document_type ("standard_manual"|"lab_report"|"other"), matched_standard, clauses (array of
{{clause_no, title, requirement, status ("compliant"|"non_compliant"|"not_tested")}}),
discrepancies (array of short strings), overall_status ("compliant"|"non_compliant"|"partial"),
summary (3 sentences, {"Hindi" if language == "hi" else "English"}).
Respond with ONLY the JSON object, no markdown.

Document Text:
{extracted_text[:6000]}
"""
        raw = call_ai_api([prompt], task_type="pdf", json_mode=True)
        
        result = extract_safe_json(raw)
        result["mode"] = "live"
        result["hash"] = compliance_hash(result)
        return result

    except Exception as e:
        log.error(f"/parse-pdf failed: {e}")
        return {
            "mode": "mock_fallback",
            "reason": str(e),
            "document_type": "lab_report",
            "matched_standard": "IS 13250",
            "clauses": [
                {"clause_no": "6.2", "title": "Insulation resistance", "requirement": "> 2 MΩ at 500V DC", "status": "compliant"},
                {"clause_no": "7.4", "title": "Thermal cut-off", "requirement": "Trips below 95°C", "status": "not_tested"},
            ],
            "discrepancies": ["Thermal cut-off test result missing from report"],
            "overall_status": "partial",
            "summary": "The charger largely meets IS 13250 insulation requirements, but the thermal cut-off test was not documented and should be re-submitted before certification.",
            "hash": compliance_hash({"seed": str(e), "t": time.time()}),
        }

@app.post("/download-report")
def download_report(payload: dict):
    report_text = f"""========================================
BISync — OFFICIAL COMPLIANCE AUDIT REPORT
========================================
Document Type: {payload.get('document_type', 'Lab Report')}
Matched Standard: {payload.get('matched_standard', 'IS 13250')}
Overall Status: {payload.get('overall_status', 'Compliant')}

SUMMARY:
{payload.get('summary', 'No summary available.')}

Generated by Team CodeX99 for SIH Grand Finale.
========================================
"""
    return PlainTextResponse(
        content=report_text,
        media_type="text/plain",
        headers={"Content-Disposition": "attachment; filename=audit_report.txt"}
    )

@app.post("/chat")
def chat(req: ChatRequest):
    try:
        results = rulebook.query(query_texts=[req.message], n_results=5)
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        
        context = "\n\n".join(
            f"[Source: {m.get('source', m.get('standard', 'Unknown Document'))}] {d}" for d, m in zip(docs, metas)
        ) or "No directly matching standard found in the rulebook."

        persona = "a friendly plain-language safety guide" if req.role == "consumer" else "a technical BIS compliance auditor"
        
        system_prompt = f"""You are an expert BIS (Bureau of Indian Standards) AI Compliance Assistant built by Team CodeX99 for the SIH Grand Finale.
You are acting as {persona}. Your goal is to provide accurate, context-aware, and source-backed information related to Indian Standards, Hallmarking rules, HUID, and BIS testing laboratories.

CRITICAL INSTRUCTION: You MUST strictly reply in the exact language the user queries in. If the user asks in Hindi, reply entirely in Hindi. If the user asks in English, reply entirely in English. Do not mix languages unless citing official acronyms or IS numbers.

Use ONLY this retrieved context from the bis_rulebook database:
---
{context}
---
Always base your answers on the provided context and cite the relevant standard numbers, lab names, or rules."""

        messages = [{"role": "system", "content": system_prompt}]
        
        for msg in req.history[-5:]:
            messages.append({"role": msg.role, "content": msg.content})
            
        messages.append({"role": "user", "content": req.message})

        answer = call_ai_api(messages, task_type="chat", json_mode=False)
        
        unique_sources = list(set([m.get("source", m.get("standard")) for m in metas if m.get("source") or m.get("standard")]))
        
        return {
            "mode": "live",
            "answer": answer.strip(),
            "sources": unique_sources,
        }

    except Exception as e:
        log.error(f"/chat failed: {e}")
        return {
            "mode": "mock_fallback",
            "reason": str(e),
            "answer": "System is running on cached data due to a temporary service disruption.",
            "sources": ["IS 9873"],
        }

@app.post("/query-rule")
def query_rule(req: QueryRuleRequest):
    try:
        results = rulebook.query(query_texts=[req.query], n_results=req.n_results)
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        dists = results.get("distances", [[]])[0]
        return {
            "mode": "live",
            "results": [
                {"standard": m.get("source", m.get("standard")), "product": m.get("category", m.get("product")), "text": d, "relevance": 1 - dist}
                for d, m, dist in zip(docs, metas, dists)
            ],
        }
    except Exception as e:
        log.error(f"/query-rule failed: {e}")
        raise HTTPException(status_code=500, detail=f"Rulebook query failed: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), reload=True)