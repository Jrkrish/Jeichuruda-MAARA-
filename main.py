from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import os, requests

API_KEY = os.getenv("CONTENTSTACK_API_KEY")
DELIVERY_TOKEN = os.getenv("CONTENTSTACK_DELIVERY_TOKEN")
ENVIRONMENT = os.getenv("CONTENTSTACK_ENVIRONMENT")
BASE = os.getenv("CONTENTSTACK_BASE_URL", "https://eu-cdn.contentstack.com")
CONTENT_TYPE = os.getenv("CS_CONTENT_TYPE", "product")
BRANCH = "main"

app = FastAPI()

# ✅ Enable CORS for Contentstack UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://eu-app.contentstack.com",
        "https://app.contentstack.com",
        "https://azure-na-app.contentstack.com"
    ],
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)

class QueryBody(BaseModel):
    query: str
    limit: int | None = 10

def contentstack_entries(q: str, limit: int) -> List[Dict[str, Any]]:
    url = f"{BASE}/v3/content_types/{CONTENT_TYPE}/entries"
    headers = {
        "api_key": API_KEY,
        "access_token": DELIVERY_TOKEN
    }
    query_param = {
        "$or": [
            {"title": {"$regex": q, "$options": "i"}},
            {"summary": {"$regex": q, "$options": "i"}}
        ]
    }
    params = {
        "environment": ENVIRONMENT,
        "branch": BRANCH,
        "limit": limit,
        "query": str(query_param).replace("'", '"')
    }
    r = requests.get(url, headers=headers, params=params, timeout=15)
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=f"CDN error: {r.text}")
    data = r.json()
    results = []
    for e in data.get("entries", []):
        results.append({
            "title": e.get("title"),
            "summary": e.get("summary") or e.get("body", "")[:180],
            "uid": e.get("uid"),
            "updated_at": e.get("updated_at")
        })
    return results

@app.post("/api/semantic-search")
def semantic_search(body: QueryBody):
    if not body.query.strip():
        return {"results": []}
    return {"results": contentstack_entries(body.query.strip(), body.limit or 10)}

@app.get("/")
def read_root():
    return {"message": "Welcome to the Contentstack API!"}
