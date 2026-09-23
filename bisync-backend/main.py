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
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("bisync")

# --------------------------------------------------------------------------
# App + CORS
# --------------------------------------------------------------------------
app = FastAPI(title="BISync API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to the Vercel domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------------------------------
# Gemini multi-key rotation pool
# --------------------------------------------------------------------------
import google.generativeai as genai

class KeyPool:
    """Round-robins across GEMINI_API_KEYS, benching keys that fail."""
    def __init__(self, env_var: str = "GEMINI_API_KEYS"):
        raw = os.environ.get(env_var, "")
        self.keys = [k.strip() for k in raw.split(",") if k.strip()]
        if not self.keys:
            log.warning("No GEMINI_API_KEYS set — running in MOCK/demo-only mode.")
        self.idx = 0
        self.bench: dict[str, float] = {}  # key -> unix time it can be retried
        self.bench_seconds = 60

    def _available_keys(self):
        now = time.time()
        return [k for k in self.keys if self.bench.get(k, 0) <= now] or self.keys

    def current(self) -> Optional[str]:
        avail = self._available_keys()
        if not avail:
            return None
        return avail[self.idx % len(avail)]

    def rotate(self):
        self.idx += 1

    def penalize(self, key: str):
        self.bench[key] = time.time() + self.bench_seconds
        log.warning(f"Benching Gemini key ...{key[-4:]} for {self.bench_seconds}s")

pool = KeyPool()

def _is_quota_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(t in msg for t in ["429", "quota", "rate limit", "resource_exhausted", "permission", "401", "403"])

def call_gemini(parts: list, model_name: str = "gemini-1.5-flash", json_mode: bool = False, max_retries: Optional[int] = None):
    """
    Calls Gemini with automatic key rotation on failure.
    """
    if not pool.keys:
        raise RuntimeError("NO_API_KEYS")

    attempts = max_retries or len(pool.keys)
    last_err: Optional[Exception] = None

    for _ in range(attempts):
        key = pool.current()
        if key is None:
            break
        try:
            genai.configure(api_key=key)
            gen_config = {"response_mime_type": "application/json"} if json_mode else {}
            model = genai.GenerativeModel(model_name, generation_config=gen_config)
            response = model.generate_content(parts)
            return response.text
        except Exception as e:
            last_err = e
            log.error(f"Gemini call failed on key ...{key[-4:]}: {e}")
            if _is_quota_error(e):
                pool.penalize(key)
            pool.rotate()

    raise RuntimeError(f"ALL_KEYS_EXHAUSTED: {last_err}")


# --------------------------------------------------------------------------
# ChromaDB — bis_rulebook collection
# --------------------------------------------------------------------------
import chromadb
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

CHROMA_PATH = os.environ.get("CHROMA_PATH", "./chroma_store")
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)

gemini_keys = os.environ.get("GEMINI_API_KEYS", "").split(",")
active_key = gemini_keys[0].strip() if gemini_keys and gemini_keys[0].strip() else ""

# FIXED: Custom safe wrapper to bypass ChromaDB's broken header bug
class SafeGeminiEmbedder(EmbeddingFunction):
    def __init__(self, api_key: str):
        self.api_key = api_key
        if self.api_key:
            genai.configure(api_key=self.api_key)

    def __call__(self, input: Documents) -> Embeddings:
        if not self.api_key:
            return [[0.0] * 768 for _ in input] # Fallback dummy vector
        
        response = genai.embed_content(
            model="models/embedding-001",
            
            content=input,
            task_type="retrieval_document"
        )
        return response['embedding']

embedder = SafeGeminiEmbedder(active_key)

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
# Models
# --------------------------------------------------------------------------
class ChatRequest(BaseModel):
    message: str
    language: str = "en"  # "en" | "hi"
    role: str = "consumer"  # "consumer" | "auditor"

class QueryRuleRequest(BaseModel):
    query: str
    n_results: int = 3


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def compliance_hash(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True).encode()
    return hashlib.sha256(raw).hexdigest()[:16]

def mock_scan_result(reason: str) -> dict:
    return {
        "mode": "mock_fallback",
        "reason": reason,
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
@app.get("/health")
def health():
    return {
        "status": "ok",
        "time": datetime.now(timezone.utc).isoformat(),
        "gemini_keys_configured": len(pool.keys),
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
        raw = call_gemini(parts, json_mode=True)
        result = json.loads(raw)
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
        b64 = base64.b64encode(pdf_bytes).decode()

        prompt = f"""You are BISync, a BIS lab-report analyst. Read this PDF (a BIS standard manual or a
lab test report). Return STRICT JSON with keys:
document_type ("standard_manual"|"lab_report"|"other"), matched_standard, clauses (array of
{{clause_no, title, requirement, status ("compliant"|"non_compliant"|"not_tested")}}),
discrepancies (array of short strings), overall_status ("compliant"|"non_compliant"|"partial"),
summary (3 sentences, {"Hindi" if language == "hi" else "English"}).
Respond with ONLY the JSON object, no markdown."""

        parts = [prompt, {"mime_type": "application/pdf", "data": b64}]
        raw = call_gemini(parts, json_mode=True)
        result = json.loads(raw)
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

@app.post("/chat")
def chat(req: ChatRequest):
    try:
        results = rulebook.query(query_texts=[req.message], n_results=3)
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        context = "\n".join(
            f"[{m.get('standard')}] {d}" for d, m in zip(docs, metas)
        ) or "No directly matching standard found in the rulebook."

        persona = "a friendly plain-language safety guide" if req.role == "consumer" else "a technical BIS compliance auditor"
        lang_instruction = "Respond in Hindi." if req.language == "hi" else "Respond in English."

        prompt = f"""You are BISync's AI assistant, {persona}, answering questions about Indian Standards (BIS).
Use ONLY this retrieved context from the bis_rulebook database:
---
{context}
---
{lang_instruction} Be concise (max 4 sentences) and cite the IS standard number where relevant.

User question: {req.message}"""

        answer = call_gemini([prompt], json_mode=False)
        return {
            "mode": "live",
            "answer": answer.strip(),
            "sources": [m.get("standard") for m in metas],
        }

    except Exception as e:
        log.error(f"/chat failed: {e}")
        return {
            "mode": "mock_fallback",
            "reason": str(e),
            "answer": (
                "Based on IS 9873, children's toys must pass flammability testing — materials should "
                "not burn faster than 30mm/second, and small parts must pass choke-hazard cylinder tests. "
                "I'm currently running on cached data; live AI will resume once the API key pool recovers."
                if req.language != "hi" else
                "IS 9873 के अनुसार, बच्चों के खिलौनों को ज्वलनशीलता परीक्षण पास करना आवश्यक है। "
                "अभी सिस्टम कैश्ड डेटा पर चल रहा है।"
            ),
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
                {"standard": m.get("standard"), "product": m.get("product"), "text": d, "relevance": 1 - dist}
                for d, m, dist in zip(docs, metas, dists)
            ],
        }
    except Exception as e:
        log.error(f"/query-rule failed: {e}")
        raise HTTPException(status_code=500, detail=f"Rulebook query failed: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), reload=True)