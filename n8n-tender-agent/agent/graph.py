"""
Graphe LangGraph principal pour l'agent de veille et réponse aux appels d'offres.

Architecture du graphe :

  ┌──────────┐
  │  scrape   │  ← Scraping BOAMP, PLACE, TED
  └────┬─────┘
       │
       ▼
  ┌──────────┐
  │ analyze   │  ← Analyse de pertinence via LLM
  └────┬─────┘
       │
       ▼
  ┌──────────┐
  │  decide   │  ← Routage conditionnel
  └──┬──┬──┬─┘
     │  │  │
     ▼  │  ▼
  ┌────┐│┌─────────────────┐
  │skip│││generate_response│  ← Génération mémoire technique
  └──┬─┘│└───────┬─────────┘
     │  │        │
     │  ▼        ▼
     │ ┌──────────┐
     │ │  notify   │  ← Notifications email/webhook
     │ └────┬─────┘
     │      │
     ▼      ▼
  ┌──────────┐
  │   END     │
  └──────────┘
"""
from __future__ import annotations

import asyncio
import logging
from copy import deepcopy

from langgraph.graph import StateGraph, END

from .state import AgentState, Tender, TenderStatus
from .nodes import (
    node_scrape,
    node_analyze,
    node_decide,
    node_generate_response,
    node_notify,
    node_skip,
)

logger = logging.getLogger(__name__)


def build_tender_graph() -> StateGraph:
    """
    Construit le graphe LangGraph pour le traitement des appels d'offres.
    Retourne un graphe compilé prêt à être exécuté.
    """
    graph = StateGraph(AgentState)

    # Ajouter les nœuds
    graph.add_node("scrape", node_scrape)
    graph.add_node("analyze", node_analyze)
    graph.add_node("generate_response", node_generate_response)
    graph.add_node("notify", node_notify)
    graph.add_node("skip", node_skip)

    # Point d'entrée
    graph.set_entry_point("scrape")

    # Transitions
    graph.add_edge("scrape", "analyze")

    # Routage conditionnel après l'analyse
    graph.add_conditional_edges(
        "analyze",
        node_decide,
        {
            "generate_response": "generate_response",
            "notify": "notify",
            "skip": "skip",
        },
    )

    # Après génération de réponse → notifier
    graph.add_edge("generate_response", "notify")

    # Fins
    graph.add_edge("notify", END)
    graph.add_edge("skip", END)

    return graph.compile()


async def run_full_pipeline(tenders: list[Tender] | None = None) -> list[dict]:
    """
    Exécute le pipeline complet :
    1. Scrape (ou utilise les tenders fournis)
    2. Analyse chaque AO
    3. Génère des réponses pour les AO pertinents
    4. Retourne les résultats

    Args:
        tenders: Liste de Tenders à analyser (si None, scrape automatiquement)

    Returns:
        Liste de résultats avec analyses et réponses
    """
    graph = build_tender_graph()
    all_results = []

    # Si pas de tenders fournis, on scrape
    if tenders is None:
        initial_state = AgentState()
        state = await graph.ainvoke(initial_state)
        if isinstance(state, dict):
            scraped_tenders = state.get("tenders", [])
        else:
            scraped_tenders = state.tenders
    else:
        scraped_tenders = tenders

    logger.info(f"📋 Traitement de {len(scraped_tenders)} appels d'offres")

    # Traiter chaque AO individuellement
    for tender in scraped_tenders:
        logger.info(f"\n{'='*60}")
        logger.info(f"📄 Traitement: {tender.title[:80]}")
        logger.info(f"{'='*60}")

        state = AgentState(
            tenders=scraped_tenders,
            current_tender=tender,
            catalogue_formations=[],
        )

        try:
            # On saute le scrape pour les AO individuels
            # et on va directement à l'analyse
            analysis_graph = _build_analysis_graph()
            result = await analysis_graph.ainvoke(state)

            if isinstance(result, dict):
                all_results.extend(result.get("results", []))
            else:
                all_results.extend(result.results)

        except Exception as e:
            logger.error(f"❌ Erreur traitement {tender.id}: {e}")
            all_results.append({
                "tender_id": tender.id,
                "title": tender.title,
                "status": "error",
                "error": str(e),
            })

    return all_results


def _build_analysis_graph() -> StateGraph:
    """Construit un sous-graphe pour l'analyse d'un seul AO."""
    graph = StateGraph(AgentState)

    graph.add_node("analyze", node_analyze)
    graph.add_node("generate_response", node_generate_response)
    graph.add_node("notify", node_notify)
    graph.add_node("skip", node_skip)

    graph.set_entry_point("analyze")

    graph.add_conditional_edges(
        "analyze",
        node_decide,
        {
            "generate_response": "generate_response",
            "notify": "notify",
            "skip": "skip",
        },
    )

    graph.add_edge("generate_response", "notify")
    graph.add_edge("notify", END)
    graph.add_edge("skip", END)

    return graph.compile()


async def analyze_single_tender(tender_data: dict) -> dict:
    """
    Point d'entrée pour analyser un seul appel d'offres (appelé par l'API).

    Args:
        tender_data: Dictionnaire avec les données de l'AO

    Returns:
        Résultat de l'analyse et éventuellement la réponse générée
    """
    tender = Tender(
        id=tender_data.get("id", "MANUAL-001"),
        title=tender_data.get("title", ""),
        source=tender_data.get("source", "MANUAL"),
        url=tender_data.get("url", ""),
        publication_date=tender_data.get("publication_date", ""),
        deadline=tender_data.get("deadline", ""),
        description=tender_data.get("description", ""),
        buyer=tender_data.get("buyer", ""),
        cpv_codes=tender_data.get("cpv_codes", []),
        amount_estimate=tender_data.get("amount_estimate", ""),
        location=tender_data.get("location", ""),
    )

    results = await run_full_pipeline(tenders=[tender])
    return results[0] if results else {"status": "error", "error": "Aucun résultat"}
