"""
Nœuds du graphe LangGraph pour l'agent de veille et réponse aux appels d'offres.

Le graphe suit le workflow :
  scrape → analyze → decide → [generate_response | skip] → notify
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from .state import AgentState, Tender, TenderAnalysis, TenderResponse, TenderStatus
from .catalogue_loader import get_catalogue, search_formations

logger = logging.getLogger(__name__)


def _get_llm() -> ChatOpenAI:
    """Crée l'instance LLM."""
    return ChatOpenAI(
        model=os.getenv("LLM_MODEL", "gpt-4o"),
        temperature=0.3,
    )


# ─────────────────────────────────────────────────────
# NODE 1 : Scraping des appels d'offres
# ─────────────────────────────────────────────────────
async def node_scrape(state: AgentState) -> AgentState:
    """Récupère les appels d'offres depuis toutes les sources."""
    from .scraper import scrape_all_sources

    logger.info("🔍 Début du scraping des appels d'offres...")
    try:
        tenders = await scrape_all_sources(days_back=7)
        state.tenders = tenders
        state.catalogue_formations = get_catalogue()
        logger.info(f"✅ {len(tenders)} appels d'offres récupérés")
    except Exception as e:
        state.errors.append(f"Erreur scraping: {str(e)}")
        logger.error(f"❌ Erreur scraping: {e}")

    return state


# ─────────────────────────────────────────────────────
# NODE 2 : Analyse de pertinence d'un appel d'offres
# ─────────────────────────────────────────────────────
async def node_analyze(state: AgentState) -> AgentState:
    """Analyse la pertinence d'un appel d'offres par rapport au catalogue."""
    if not state.current_tender:
        return state

    tender = state.current_tender
    state.status = TenderStatus.ANALYZING
    llm = _get_llm()

    catalogue_summary = _format_catalogue_summary()

    system_prompt = """Tu es un expert en marchés publics français spécialisé dans la formation professionnelle.
Tu travailles pour Paris Nord Business School (PNBS), un organisme de formation continue.

Ton rôle est d'analyser les appels d'offres pour déterminer s'ils correspondent aux formations proposées par PNBS.

CRITÈRES D'ANALYSE :
1. Correspondance thématique avec le catalogue de formations
2. Capacité à répondre aux lots/prestations demandées
3. Zone géographique (Île-de-France prioritaire)
4. Budget estimé vs tarifs du catalogue
5. Délais de réponse réalistes
6. Certifications/labels requis vs ceux détenus

Tu dois être SÉLECTIF : ne recommande que les AO où PNBS a de réelles chances."""

    user_prompt = f"""Analyse cet appel d'offres :

TITRE : {tender.title}
SOURCE : {tender.source}
ACHETEUR : {tender.buyer}
DESCRIPTION : {tender.description}
DATE PUBLICATION : {tender.publication_date}
DATE LIMITE : {tender.deadline}
LOCALISATION : {tender.location}
MONTANT ESTIMÉ : {tender.amount_estimate}
CODES CPV : {', '.join(tender.cpv_codes)}

---

CATALOGUE PNBS (résumé) :
{catalogue_summary}

---

Réponds en JSON strict avec cette structure :
{{
  "relevance_score": 0.0 à 1.0,
  "matching_formations": ["ID-001: Titre formation", ...],
  "strengths": ["force 1", "force 2"],
  "weaknesses": ["faiblesse 1"],
  "recommended_action": "REPONDRE" | "SURVEILLER" | "IGNORER",
  "summary": "Résumé en 2-3 phrases",
  "estimated_effort": "X jours"
}}"""

    try:
        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])

        # Parser la réponse JSON
        content = response.content
        # Extraire le JSON du markdown si nécessaire
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        analysis_data = json.loads(content.strip())

        state.analysis = TenderAnalysis(
            tender_id=tender.id,
            relevance_score=float(analysis_data.get("relevance_score", 0)),
            matching_formations=[
                {"id": f.split(":")[0].strip(), "title": f.split(":")[-1].strip()}
                for f in analysis_data.get("matching_formations", [])
            ],
            strengths=analysis_data.get("strengths", []),
            weaknesses=analysis_data.get("weaknesses", []),
            recommended_action=analysis_data.get("recommended_action", "IGNORER"),
            summary=analysis_data.get("summary", ""),
            estimated_effort=analysis_data.get("estimated_effort", ""),
        )

        if state.analysis.relevance_score >= 0.6:
            state.status = TenderStatus.RELEVANT
        else:
            state.status = TenderStatus.NOT_RELEVANT

        logger.info(
            f"📊 Analyse {tender.id}: score={state.analysis.relevance_score:.2f}, "
            f"action={state.analysis.recommended_action}"
        )

    except Exception as e:
        state.errors.append(f"Erreur analyse {tender.id}: {str(e)}")
        state.status = TenderStatus.ERROR
        logger.error(f"❌ Erreur analyse: {e}")

    return state


# ─────────────────────────────────────────────────────
# NODE 3 : Décision (routage conditionnel)
# ─────────────────────────────────────────────────────
def node_decide(state: AgentState) -> str:
    """Décide si on génère une réponse ou si on passe."""
    if state.analysis and state.analysis.recommended_action == "REPONDRE":
        return "generate_response"
    elif state.analysis and state.analysis.recommended_action == "SURVEILLER":
        return "notify"
    return "skip"


# ─────────────────────────────────────────────────────
# NODE 4 : Génération de la réponse à l'AO
# ─────────────────────────────────────────────────────
async def node_generate_response(state: AgentState) -> AgentState:
    """Génère un brouillon de réponse pour l'appel d'offres."""
    if not state.current_tender or not state.analysis:
        return state

    tender = state.current_tender
    analysis = state.analysis
    llm = _get_llm()

    matching_details = _get_matching_formation_details(analysis.matching_formations)

    system_prompt = """Tu es un expert en rédaction de réponses aux marchés publics pour un organisme de formation.
Tu rédiges pour Paris Nord Business School (PNBS), spécialisé en formation professionnelle continue.

INFORMATIONS PNBS :
- Organisme de formation certifié Qualiopi
- 13 domaines de formation, 110+ formations au catalogue
- Formateurs experts avec 10+ ans d'expérience
- Formations éligibles CPF, OPCO, France Travail
- Taux de satisfaction > 95%
- Implantation Île-de-France, formations possibles sur tout le territoire

Rédige de manière professionnelle, structurée et conforme aux attendus des marchés publics."""

    user_prompt = f"""Génère une réponse structurée pour cet appel d'offres :

APPEL D'OFFRES :
- Titre : {tender.title}
- Acheteur : {tender.buyer}
- Description : {tender.description}
- Budget estimé : {tender.amount_estimate}
- Date limite : {tender.deadline}

ANALYSE :
- Score de pertinence : {analysis.relevance_score}
- Forces : {', '.join(analysis.strengths)}
- Points d'attention : {', '.join(analysis.weaknesses)}

FORMATIONS CORRESPONDANTES :
{matching_details}

---

Génère en JSON :
{{
  "cover_letter": "Lettre de motivation professionnelle (3-4 paragraphes)",
  "technical_memo": "Mémoire technique structuré avec sections : Compréhension du besoin, Méthodologie, Moyens, Planning, Suivi qualité",
  "proposed_formations": [
    {{
      "formation_id": "ID",
      "title": "Titre",
      "duration": "Durée",
      "price": 0,
      "customization": "Adaptation proposée pour cet AO"
    }}
  ],
  "compliance_matrix": [
    {{
      "requirement": "Exigence du cahier des charges",
      "response": "CONFORME / PARTIEL / NON CONFORME",
      "detail": "Explication"
    }}
  ]
}}"""

    try:
        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])

        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        resp_data = json.loads(content.strip())

        state.response = TenderResponse(
            tender_id=tender.id,
            cover_letter=resp_data.get("cover_letter", ""),
            technical_memo=resp_data.get("technical_memo", ""),
            proposed_formations=resp_data.get("proposed_formations", []),
            compliance_matrix=resp_data.get("compliance_matrix", []),
        )
        state.status = TenderStatus.RESPONSE_DRAFTED

        logger.info(f"📝 Réponse générée pour {tender.id}")

    except Exception as e:
        state.errors.append(f"Erreur génération réponse {tender.id}: {str(e)}")
        state.status = TenderStatus.ERROR
        logger.error(f"❌ Erreur génération: {e}")

    return state


# ─────────────────────────────────────────────────────
# NODE 5 : Notification
# ─────────────────────────────────────────────────────
async def node_notify(state: AgentState) -> AgentState:
    """Prépare les notifications pour les résultats."""
    if not state.current_tender:
        return state

    tender = state.current_tender
    analysis = state.analysis

    notification = {
        "tender_id": tender.id,
        "title": tender.title,
        "source": tender.source,
        "status": state.status.value,
        "url": tender.url,
        "deadline": tender.deadline,
    }

    if analysis:
        notification.update({
            "relevance_score": analysis.relevance_score,
            "recommended_action": analysis.recommended_action,
            "summary": analysis.summary,
            "matching_formations": len(analysis.matching_formations),
        })

    if state.response:
        notification["has_draft_response"] = True

    state.notifications.append(notification)
    state.results.append({
        "tender": asdict(tender),
        "analysis": asdict(analysis) if analysis else None,
        "response": asdict(state.response) if state.response else None,
        "status": state.status.value,
    })

    logger.info(f"🔔 Notification préparée pour {tender.id}")
    return state


# ─────────────────────────────────────────────────────
# NODE 6 : Skip (AO non pertinent)
# ─────────────────────────────────────────────────────
async def node_skip(state: AgentState) -> AgentState:
    """Marque un AO comme non pertinent et passe au suivant."""
    if state.current_tender:
        state.results.append({
            "tender_id": state.current_tender.id,
            "title": state.current_tender.title,
            "status": "skipped",
            "reason": state.analysis.summary if state.analysis else "Non pertinent",
        })
        logger.info(f"⏭️ AO ignoré: {state.current_tender.title[:60]}")
    return state


# ─────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────
def _format_catalogue_summary() -> str:
    """Formate un résumé du catalogue pour le prompt."""
    catalogue = get_catalogue()
    domains = {}
    for f in catalogue:
        d = f["domain"]
        if d not in domains:
            domains[d] = []
        domains[d].append(f)

    lines = []
    for domain, formations in domains.items():
        lines.append(f"\n## {domain} ({len(formations)} formations)")
        for f in formations:
            cpf_tag = " [CPF]" if f["cpf"] else ""
            cert_tag = f" [{f['certification']}]" if f.get("certification") else ""
            lines.append(f"  - {f['id']}: {f['title']} ({f['duration']}, {f['price']}€){cpf_tag}{cert_tag}")

    return "\n".join(lines)


def _get_matching_formation_details(matching: list[dict]) -> str:
    """Récupère les détails des formations correspondantes."""
    catalogue = get_catalogue()
    details = []
    matching_ids = {m.get("id", "") for m in matching}

    for f in catalogue:
        if f["id"] in matching_ids:
            details.append(
                f"- {f['id']}: {f['title']}\n"
                f"  Durée: {f['duration']} | Prix: {f['price']}€ | CPF: {'Oui' if f['cpf'] else 'Non'}\n"
                f"  Certification: {f.get('certification', 'N/A')}\n"
                f"  Public: {f['target']}"
            )

    return "\n".join(details) if details else "Aucune formation spécifiquement identifiée"
