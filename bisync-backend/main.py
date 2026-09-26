"""
BISync — FastAPI backend
Team CodeX99 · SIH26107 — AI-Powered Intelligent Assistant for Indian Standards & BIS Services
"""

import os
import json
import time
import base64
import hashlib
import logging
import requests
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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------------------------------
# Direct REST API Integration (Strict AIza Format Failsafe)
# --------------------------------------------------------------------------
def call_gemini_direct(parts: list, model_name: str = "gemini-1.5-flash", json_mode: bool = False):
    """Hits Google Gemini REST API directly with a strict AIza key format check."""
    api_keys_str = os.environ.get("GEMINI_API_KEYS", "")
    keys = [k.strip() for k in api_keys_str.split(",") if k.strip()]
    
    if not keys:
        raise RuntimeError("NO_GEMINI_API_KEY_FOUND_IN_ENV")

    current_key = keys[0]
    
    # 🚨 FAILSAFE: Strictly block anything that is not a real API Key
    if not current_key.startswith("AIza"):
        error_msg = f"INVALID_KEY_FORMAT: Gemini API keys MUST start with 'AIza'. You are using an invalid token starting with '{current_key[:5]}...'. Please generate a FRESH key."
        log.error(error_msg)
        raise RuntimeError(error_msg)

    # Standard URL format for AIza API keys
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={current_key}"
    headers = {"Content-Type": "application/json"}

    # Format payload exactly as Google REST API expects
    formatted_contents = []
    for p in parts:
        if isinstance(p, str):
            formatted_contents.append({"text": p})
        elif isinstance(p, dict) and "data" in p:
            mime = p.get("mime_type", "image/jpeg")
            formatted_contents.append({
                "inline_data": {
                    "mime_type": mime,
                    "data": p["data"]
                }
            })

    payload = {
        "contents": [{"parts": formatted_contents}]
    }

    if json_mode:
        payload["generationConfig"] = {"responseMimeType": "application/json"}

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code != 200:
            log.error(f"Google API Error: {response.status_code} - {response.text}")
            raise RuntimeError(f"GEMINI_REST_ERROR: {response.status_code} | {response.text}")

        data = response.json()
        result_text = data["candidates"][0]["content"]["parts"][0]["text"]
        
        if json_mode:
             result_text = result_text.replace("```json", "").replace("