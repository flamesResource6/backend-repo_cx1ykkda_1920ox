import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any

# Database helpers
try:
    from database import db, create_document, get_documents
except Exception:
    db = None
    def create_document(*args, **kwargs):
        raise Exception("Database not available. Check DATABASE_URL and DATABASE_NAME env vars.")
    def get_documents(*args, **kwargs):
        raise Exception("Database not available. Check DATABASE_URL and DATABASE_NAME env vars.")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------
# Models
# -----------------
class DemoRequestIn(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    company: Optional[str] = None
    message: Optional[str] = None

class DemoRequestOut(BaseModel):
    id: str
    email: EmailStr
    name: Optional[str] = None
    company: Optional[str] = None

class MetricsOut(BaseModel):
    metrics: List[Dict[str, Any]]

# -----------------
# Core endpoints
# -----------------
@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI Backend!"}

@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "database": bool(db) and "available" or "unavailable",
        "version": "1.0.0"
    }

# -----------------
# Demo Requests
# -----------------
@app.post("/api/demo-requests", response_model=DemoRequestOut)
def create_demo_request(payload: DemoRequestIn):
    try:
        # Prepare document
        data = payload.model_dump()
        # Persist
        new_id = create_document("demorequest", data)
        return {
            "id": new_id,
            "email": payload.email,
            "name": payload.name,
            "company": payload.company,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -----------------
# Metrics endpoint (for Insights)
# -----------------
@app.get("/api/metrics", response_model=MetricsOut)
def get_metrics():
    # Provide synthetic metrics; augment with live counts if DB available
    base_metrics = [
        {"label": "EHR Feeds", "value": 142, "hint": "+12 this week"},
        {"label": "Claims/day", "value": "1.8M", "hint": "EDI 837/835"},
        {"label": "Avg. Latency", "value": "320ms", "hint": "stream pipelines"},
        {"label": "AI Models", "value": 28, "hint": "risk & quality"},
    ]
    try:
        if db:
            try:
                demo_count = db["demorequest"].count_documents({})
                base_metrics.append({
                    "label": "Demo Requests", "value": demo_count, "hint": "total received"
                })
            except Exception:
                pass
    except Exception:
        pass
    return {"metrics": base_metrics}

# -----------------
# Database test endpoint (kept for diagnostics)
# -----------------
@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
