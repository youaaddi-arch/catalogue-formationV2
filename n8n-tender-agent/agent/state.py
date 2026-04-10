"""
État partagé du graphe LangGraph pour l'agent de veille appels d'offres.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TenderStatus(str, Enum):
    NEW = "new"
    ANALYZING = "analyzing"
    RELEVANT = "relevant"
    NOT_RELEVANT = "not_relevant"
    RESPONSE_DRAFTED = "response_drafted"
    RESPONSE_SENT = "response_sent"
    ERROR = "error"


@dataclass
class Tender:
    """Représente un appel d'offres détecté."""
    id: str
    title: str
    source: str  # BOAMP, PLACE, TED, etc.
    url: str
    publication_date: str
    deadline: str
    description: str
    buyer: str = ""
    cpv_codes: list[str] = field(default_factory=list)
    amount_estimate: str = ""
    location: str = ""
    lots: list[dict] = field(default_factory=list)
    raw_data: dict = field(default_factory=dict)


@dataclass
class TenderAnalysis:
    """Résultat de l'analyse d'un appel d'offres."""
    tender_id: str
    relevance_score: float  # 0.0 à 1.0
    matching_formations: list[dict] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    recommended_action: str = ""
    summary: str = ""
    estimated_effort: str = ""


@dataclass
class TenderResponse:
    """Réponse générée pour un appel d'offres."""
    tender_id: str
    technical_memo: str = ""
    proposed_formations: list[dict] = field(default_factory=list)
    pricing_proposal: dict = field(default_factory=dict)
    cover_letter: str = ""
    compliance_matrix: list[dict] = field(default_factory=list)


@dataclass
class AgentState:
    """État global du graphe LangGraph."""
    # Entrée
    tenders: list[Tender] = field(default_factory=list)
    catalogue_formations: list[dict] = field(default_factory=list)

    # Traitement
    current_tender: Tender | None = None
    status: TenderStatus = TenderStatus.NEW
    analysis: TenderAnalysis | None = None
    response: TenderResponse | None = None

    # Sorties
    results: list[dict] = field(default_factory=list)
    notifications: list[dict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    # Metadata
    messages: list[Any] = field(default_factory=list)
