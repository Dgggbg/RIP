"""
FastAPI Server v2 — Multilingual Clinical RAG
---------------------------------------------
Serves the multilingual chat UI frontend and exposes the RAG API.

Run:
    python server.py
Then open: http://localhost:8000
"""

import os
os.environ["OPENBLAS_NUM_THREADS"] = "1"

import sys
from pathlib import Path
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import config
from query import load_index, retrieve
from generate import generate_grounded_answer

app = FastAPI(
    title="Clinical Decision Support RAG API",
    description="Multilingual Grounded Medical RAG — ChromaDB + Gemini",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UI_DIR = BASE_DIR / "ui"
if UI_DIR.exists():
    app.mount("/ui", StaticFiles(directory=str(UI_DIR)), name="ui_static")


# ── No-Cache Middleware (dev mode — forces fresh JS/CSS every load) ────────────
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest

class NoCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/ui/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

app.add_middleware(NoCacheMiddleware)



# ── Models ────────────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Clinical question")


# ── API Endpoints ─────────────────────────────────────────────────────────────

@app.get("/api/health", summary="Health check")
def health():
    return {
        "status": "ok",
        "chroma_ready": config.CHROMA_DIR.exists(),
        "gemini_configured": bool(config.GEMINI_API_KEY),
        "model": config.GEMINI_MODEL,
        "embedding": config.EMBEDDING_PROVIDER,
    }


@app.post("/api/query", summary="Send a clinical question to the RAG pipeline")
def query(req: QueryRequest):
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    if not config.CHROMA_DIR.exists():
        raise HTTPException(
            status_code=503,
            detail="Vector index not found. Please run ingestion first (python ingest.py).",
        )

    try:
        # Translate non-English questions to English for retrieval
        english_query = translate_to_english(question)

        vectordb = load_index()
        # Use the English translation for vector search
        results = retrieve(vectordb, english_query)
        # Pass original question to generation so Gemini answers in user's language
        response = generate_grounded_answer(question, results)
        return response
    except SystemExit:
        raise HTTPException(status_code=503, detail="Vector database is not available.")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


def translate_to_english(text: str) -> str:
    """Translates a question to English using Gemini if it appears non-English.
    Returns the original text if it's already English or translation fails."""
    import re

    # Quick heuristic: if >80% ASCII letters, it's likely English already
    ascii_letters = sum(1 for c in text if c.isascii() and c.isalpha())
    total_letters = sum(1 for c in text if c.isalpha())
    if total_letters == 0 or (ascii_letters / total_letters) > 0.8:
        return text

    # Use Gemini to translate
    api_key = config.GEMINI_API_KEY
    if not api_key:
        return text  # Can't translate without API key, use original

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=f"Translate the following medical question to English. Return ONLY the English translation, nothing else:\n\n{text}",
        )
        translated = response.text.strip()
        if translated:
            print(f"[Translation] '{text}' → '{translated}'")
            return translated
    except Exception as e:
        print(f"[Translation Error] {e}")

    return text  # Fallback to original


# ── Frontend ──────────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
def frontend():
    index_path = UI_DIR / "index.html"
    if index_path.exists():
        content = index_path.read_text(encoding="utf-8")
        return HTMLResponse(content=content)
    return HTMLResponse(
        "<h2>UI not found. Make sure the <code>ui/</code> directory exists.</h2>",
        status_code=404,
    )


# ── Entry ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)
