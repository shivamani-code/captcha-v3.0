import os
import json
import uuid
import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Request

STORAGE_FILE = os.path.join(os.path.dirname(__file__), ".hindsight_storage.json")

def load_storage() -> Dict[str, List[Dict[str, Any]]]:
    if os.path.exists(STORAGE_FILE):
        try:
            with open(STORAGE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_storage(data: Dict[str, List[Dict[str, Any]]]):
    with open(STORAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

mock_hindsight_app = FastAPI(title="Hindsight Memory Service")

@mock_hindsight_app.get("/version")
def get_version():
    return {
        "api_version": "0.10.1",
        "features": {
            "observations": True,
            "mcp": True,
            "worker": True,
            "bank_config_api": True,
            "bank_llm_health": True,
            "file_upload_api": True,
            "document_export_api": True,
            "document_import_api": True,
            "audit_log": True,
            "llm_trace": True,
            "store_document_text": True,
        },
    }

@mock_hindsight_app.post("/v1/default/banks/{bank_id}/memories")
async def retain_memories(bank_id: str, request: Request):
    payload = await request.json()
    items = payload.get("items", [])
    storage = load_storage()
    if bank_id not in storage:
        storage[bank_id] = []

    created_ids = []
    for item in items:
        mem_id = uuid.uuid4().hex
        content = item.get("content", "")
        if isinstance(content, list):
            content = " ".join(str(b.get("text", "")) for b in content)
        
        entry = {
            "id": mem_id,
            "text": str(content),
            "tags": item.get("tags") or [],
            "metadata": item.get("metadata") or {},
            "occurred_start": item.get("timestamp") or datetime.now(timezone.utc).isoformat(),
        }
        storage[bank_id].append(entry)
        created_ids.append(mem_id)

    save_storage(storage)
    return {
        "success": True,
        "bank_id": bank_id,
        "items_count": len(created_ids),
        "async": False,
        "operation_id": uuid.uuid4().hex,
        "operation_ids": created_ids,
    }

@mock_hindsight_app.post("/v1/default/banks/{bank_id}/memories/recall")
async def recall_memories(bank_id: str, request: Request):
    payload = await request.json()
    query = (payload.get("query") or "").lower()
    query_tags = set(payload.get("tags") or [])
    storage = load_storage()
    bank_memories = storage.get(bank_id, [])

    query_words = set(re.findall(r"\w+", query))

    ranked = []
    for m in bank_memories:
        mem_text = m.get("text", "").lower()
        mem_tags = set(m.get("tags") or [])
        mem_words = set(re.findall(r"\w+", mem_text))

        # Check tag overlap if tags requested
        tag_match = bool(query_tags.intersection(mem_tags)) if query_tags else True

        # Calculate word overlap score
        common_words = query_words.intersection(mem_words)
        score = len(common_words) / max(1, len(query_words))

        # Boost score if key security terms match
        for key_term in ["bot", "human", "ml", "hard_rule", "entropy", "speed"]:
            if key_term in query and key_term in mem_text:
                score += 0.2

        if tag_match and score > 0.05:
            ranked.append((m, score))

    ranked.sort(key=lambda x: x[1], reverse=True)

    results = []
    for m, score in ranked[:10]:
        results.append({
            "id": m["id"],
            "text": m["text"],
            "type": "experience",
            "tags": m["tags"],
            "metadata": m["metadata"],
            "occurred_start": m["occurred_start"],
            "scores": {"final": round(min(1.0, score), 3)},
        })

    return {
        "results": results,
        "trace": None,
        "entities": None,
        "chunks": None,
        "source_facts": None,
    }

@mock_hindsight_app.delete("/v1/default/banks/{bank_id}")
def delete_bank(bank_id: str):
    storage = load_storage()
    if bank_id in storage:
        del storage[bank_id]
        save_storage(storage)
    return {"success": True, "bank_id": bank_id}
