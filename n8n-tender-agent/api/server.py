"""
Serveur API FastAPI — pont entre N8N et l'agent LangGraph.

Endpoints :
  POST /api/analyze          — Analyser un appel d'offres
  POST /api/generate-response — Générer une réponse complète
  POST /api/results          — Sauvegarder les résultats
  GET  /api/results          — Lister les résultats
  POST /api/scrape           — Lancer un scraping manuel
  GET  /api/catalogue        — Consulter le catalogue
  GET  /api/health           — Vérification de santé
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "data" / "tender_results.db"


# ─────────────────────────────────────────────────────
# Pydantic models
# ─────────────────────────────────────────────────────
class TenderInput(BaseModel):
    id: str = ""
    title: str
    source: str = "MANUAL"
    url: str = ""
    publication_date: str = ""
    deadline: str = ""
    description: str = ""
    buyer: str = ""
    cpv_codes: list[str] = []
    amount_estimate: str = ""
    location: str = ""


class AnalyzeRequest(BaseModel):
    tender: TenderInput | dict


class GenerateResponseRequest(BaseModel):
    tender_id: str
    tender: dict
    analysis: dict


class SaveResultRequest(BaseModel):
    tender: dict
    analysis: dict = {}
    response: dict = {}
    status: str = "processed"


class ScrapeRequest(BaseModel):
    days_back: int = 7
    sources: list[str] = ["boamp", "place", "ted"]


# ─────────────────────────────────────────────────────
# Database
# ─────────────────────────────────────────────────────
def init_db():
    """Initialise la base SQLite."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tender_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tender_id TEXT UNIQUE,
            title TEXT,
            source TEXT,
            url TEXT,
            relevance_score REAL,
            recommended_action TEXT,
            status TEXT,
            analysis_json TEXT,
            response_json TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_tender_status ON tender_results(status)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_tender_score ON tender_results(relevance_score)
    """)
    conn.commit()
    conn.close()


def save_result(data: dict):
    """Sauvegarde un résultat en base."""
    conn = sqlite3.connect(str(DB_PATH))
    tender = data.get("tender", {})
    analysis = data.get("analysis", {})

    conn.execute("""
        INSERT OR REPLACE INTO tender_results
        (tender_id, title, source, url, relevance_score, recommended_action,
         status, analysis_json, response_json, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        tender.get("id", ""),
        tender.get("title", ""),
        tender.get("source", ""),
        tender.get("url", ""),
        analysis.get("relevance_score", 0),
        analysis.get("recommended_action", ""),
        data.get("status", "processed"),
        json.dumps(analysis, ensure_ascii=False),
        json.dumps(data.get("response", {}), ensure_ascii=False),
        datetime.now().isoformat(),
    ))
    conn.commit()
    conn.close()


def get_results(limit: int = 50, min_score: float = 0.0) -> list[dict]:
    """Récupère les résultats depuis la base."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT * FROM tender_results
        WHERE relevance_score >= ?
        ORDER BY created_at DESC
        LIMIT ?
    """, (min_score, limit)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


# ─────────────────────────────────────────────────────
# App FastAPI
# ─────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialisation au démarrage."""
    init_db()
    logger.info("🚀 Agent Veille AO — API démarrée")
    yield
    logger.info("👋 API arrêtée")


app = FastAPI(
    title="PNBS - Agent Veille Appels d'Offres",
    description="API pour l'agent de veille et réponse aux appels d'offres de formation",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────
@app.get("/api/health")
async def health():
    return {
        "status": "healthy",
        "service": "PNBS Tender Agent",
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/api/analyze")
async def analyze_tender(request: AnalyzeRequest):
    """Analyse un appel d'offres via LangGraph."""
    from agent.graph import analyze_single_tender

    tender_data = request.tender
    if isinstance(tender_data, TenderInput):
        tender_data = tender_data.model_dump()
    elif isinstance(tender_data, str):
        tender_data = json.loads(tender_data)

    logger.info(f"📊 Analyse AO: {tender_data.get('title', 'N/A')[:60]}")

    try:
        result = await analyze_single_tender(tender_data)
        return result
    except Exception as e:
        logger.error(f"❌ Erreur analyse: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate-response")
async def generate_response(request: GenerateResponseRequest):
    """Génère une réponse complète pour un AO pertinent."""
    from agent.graph import analyze_single_tender
    from agent.state import AgentState, Tender, TenderAnalysis

    logger.info(f"📝 Génération réponse pour: {request.tender_id}")

    try:
        # Reconstruire l'état et générer la réponse
        result = await analyze_single_tender(request.tender)
        return result
    except Exception as e:
        logger.error(f"❌ Erreur génération: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/results")
async def save_tender_result(request: SaveResultRequest):
    """Sauvegarde les résultats d'un traitement."""
    try:
        save_result(request.model_dump())
        return {"status": "saved", "tender_id": request.tender.get("id", "")}
    except Exception as e:
        logger.error(f"❌ Erreur sauvegarde: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/results")
async def list_results(limit: int = 50, min_score: float = 0.0):
    """Liste les résultats de la veille."""
    results = get_results(limit=limit, min_score=min_score)
    return {"count": len(results), "results": results}


@app.post("/api/scrape")
async def trigger_scrape(request: ScrapeRequest):
    """Lance un scraping manuel des sources d'AO."""
    from agent.scraper import scrape_all_sources

    logger.info(f"🔍 Scraping manuel: {request.sources}, {request.days_back} jours")

    try:
        tenders = await scrape_all_sources(days_back=request.days_back)
        return {
            "count": len(tenders),
            "tenders": [
                {
                    "id": t.id,
                    "title": t.title,
                    "source": t.source,
                    "url": t.url,
                    "deadline": t.deadline,
                    "buyer": t.buyer,
                }
                for t in tenders
            ],
        }
    except Exception as e:
        logger.error(f"❌ Erreur scraping: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/catalogue")
async def get_catalogue_endpoint(domain: str = "", cpf_only: bool = False, query: str = ""):
    """Consulte le catalogue de formations PNBS."""
    from agent.catalogue_loader import search_formations, get_domains

    formations = search_formations(query=query, domain=domain or None, cpf_only=cpf_only)
    return {
        "count": len(formations),
        "domains": get_domains(),
        "formations": formations,
    }


@app.get("/api/stats")
async def get_stats():
    """Statistiques de la veille."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    total = conn.execute("SELECT COUNT(*) as c FROM tender_results").fetchone()["c"]
    relevant = conn.execute(
        "SELECT COUNT(*) as c FROM tender_results WHERE relevance_score >= 0.6"
    ).fetchone()["c"]
    responded = conn.execute(
        "SELECT COUNT(*) as c FROM tender_results WHERE response_json != '{}' AND response_json != ''"
    ).fetchone()["c"]

    by_source = conn.execute(
        "SELECT source, COUNT(*) as c FROM tender_results GROUP BY source"
    ).fetchall()

    conn.close()

    return {
        "total_tenders": total,
        "relevant_tenders": relevant,
        "responses_generated": responded,
        "by_source": {row["source"]: row["c"] for row in by_source},
    }


# ─────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.server:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", "8000")),
        reload=True,
    )
