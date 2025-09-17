import os
import re
from typing import List, Dict, Any
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

API_KEY = os.getenv('CONTENTSTACK_API_KEY', 'bltdda1c327d1251b73')
DELIVERY_TOKEN = os.getenv('CONTENTSTACK_DELIVERY_TOKEN', 'csc8234bce89440911c958c6e4')
ENVIRONMENT = os.getenv('CONTENTSTACK_ENVIRONMENT', 'preview')
CONTENT_TYPE = os.getenv('CS_CONTENT_TYPE', 'Product')
BRANCH = os.getenv('CS_BRANCH', 'main')
BASE = os.getenv('CONTENTSTACK_BASE_URL', 'https://eu-cdn.contentstack.com')
API_VERSION = "v3"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)

class QueryBody(BaseModel):
    query: str
    limit: int | None = 10

def build_contentstack_regex(query: str) -> str:
    # Escape regex special chars except * (as wildcard for Contentstack)
    escaped = re.escape(query.strip())
    # Replace escaped * with regex wildcard and append * for prefix matching
    regex_query = escaped.replace(r'\\*', '.*')
    if not regex_query.endswith('.*'):
        regex_query += '.*'
    return regex_query

def query_entries(q: str, limit: int) -> List[Dict[str, Any]]:
    if not API_KEY or not DELIVERY_TOKEN:
        raise HTTPException(status_code=500, detail="Missing API credentials")

    url = f"{BASE}/{API_VERSION}/content_types/{CONTENT_TYPE}/entries"
    headers = {
        "api_key": API_KEY,
        "access_token": DELIVERY_TOKEN,
    }
    regex_query = build_contentstack_regex(q)
    query_param = {
        "$or": [
            {"title": {"$regex": regex_query, "$options": "i"}},
            {"summary": {"$regex": regex_query, "$options": "i"}}
        ]
    }
    params = {
        "environment": ENVIRONMENT,
        "branch": BRANCH,
        "limit": limit,
        "query": str(query_param).replace("'", '"'),
    }
    r = requests.get(url, headers=headers, params=params, timeout=20)
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Content Delivery error: {r.text}")

    data = r.json()
    results = []
    for e in data.get("entries", []):
        results.append({
            "title": e.get("title"),
            "summary": e.get("summary") or (e.get("body") or "")[:180],
            "uid": e.get("uid"),
            "updated_at": e.get("updated_at"),
        })
    return results

@app.post("/api/semantic-search")
def semantic_search(body: QueryBody):
    q = (body.query or "").strip()
    if not q:
        return {"results": []}
    return {"results": query_entries(q, body.limit or 10)}

@app.get("/")
def root():
    return {"ok": True, "message": "Contentstack Semantic Search API"}
