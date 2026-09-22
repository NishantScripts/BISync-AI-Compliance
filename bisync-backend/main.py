from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, text
import chromadb

app = FastAPI(title="BISync AI Backend")

# --- CORS Setup (Frontend connection ke liye) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Har website/port se request allow karega
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- MySQL Setup ---
DATABASE_URL = "mysql+pymysql://root:Nishant%402007@localhost/bisync_db"
engine = create_engine(DATABASE_URL)

# --- ChromaDB Setup ---
chroma_client = chromadb.PersistentClient(path="./chroma_db")
rule_collection = chroma_client.get_or_create_collection(name="bis_rulebook")

class RuleQueryRequest(BaseModel):
    query: str
    top_k: int = 1

@app.get("/")
def read_root():
    return {"message": "BISync AI Backend is Live and Ready!"}

@app.post("/query-rule")
def search_bis_rule(request: RuleQueryRequest):
    try:
        results = rule_collection.query(
            query_texts=[request.query],
            n_results=request.top_k
        )
        if not results["documents"] or not results["documents"][0]:
            return {"status": "not_found", "message": "No matching BIS standard found."}
        
        return {
            "status": "success",
            "query": request.query,
            "matched_id": results["ids"][0][0],
            "matched_rule": results["documents"][0][0]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))