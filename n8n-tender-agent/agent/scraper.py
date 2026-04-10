"""
Scraping des sources d'appels d'offres publics français et européens.

Sources supportées :
  - BOAMP (Bulletin Officiel des Annonces des Marchés Publics) via API OpenDataSoft
  - PLACE (Plateforme des Achats de l'État) via flux RSS
  - TED (Tenders Electronic Daily) via API
"""
from __future__ import annotations

import hashlib
import logging
import os
from datetime import datetime, timedelta

import httpx
import feedparser

from .state import Tender

logger = logging.getLogger(__name__)

BOAMP_API = os.getenv(
    "BOAMP_API_URL",
    "https://boamp-datadila.opendatasoft.com/api/explore/v2.1",
)

# Mots-clés liés à la formation professionnelle
KEYWORDS_FORMATION = [
    "formation professionnelle",
    "formation continue",
    "organisme de formation",
    "prestation de formation",
    "actions de formation",
    "plan de développement des compétences",
    "bilan de compétences",
    "VAE",
    "apprentissage",
    "certification professionnelle",
    "CPF",
    "OPCO",
    "formation management",
    "formation bureautique",
    "formation sécurité",
    "formation langues",
    "formation numérique",
    "formation digitale",
    "cybersécurité formation",
    "formation RH",
    "formation comptabilité",
    "BTP formation",
    "hôtellerie restauration formation",
    "HACCP",
    "SST",
    "CACES",
    "habilitation électrique",
]

# Codes CPV liés à la formation
CPV_FORMATION = [
    "80500000",  # Services de formation
    "80510000",  # Services de formation spécialisée
    "80511000",  # Formation du personnel
    "80521000",  # Services de programmes de formation
    "80522000",  # Séminaires de formation
    "80530000",  # Services de formation professionnelle
    "80531000",  # Services de formation industrielle et technique
    "80532000",  # Services de formation en gestion
    "80533000",  # Services de familiarisation/formation informatique
    "80533100",  # Services de formation informatique
    "80540000",  # Services de formation dans le domaine de l'environnement
    "80550000",  # Services de formation en matière de sécurité
    "80560000",  # Services de formation dans le domaine de la santé
    "80570000",  # Services de formation en développement personnel
    "80580000",  # Services de cours de langues
    "80590000",  # Services de tutorat
    "80600000",  # Formation aux équipements militaires et de sécurité
    "80610000",  # Formation/exercices aux équipements de sécurité
]


async def scrape_boamp(days_back: int = 7) -> list[Tender]:
    """
    Récupère les appels d'offres depuis le BOAMP (API OpenDataSoft).
    Filtre sur les mots-clés liés à la formation professionnelle.
    """
    tenders = []
    date_from = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

    # Requête par mots-clés formation
    keywords_query = " OR ".join(f'"{kw}"' for kw in KEYWORDS_FORMATION[:10])

    params = {
        "dataset": "boamp",
        "q": keywords_query,
        "where": f"dateparution >= '{date_from}'",
        "limit": 50,
        "offset": 0,
        "sort": "-dateparution",
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{BOAMP_API}/catalog/datasets/boamp/records", params=params)
            resp.raise_for_status()
            data = resp.json()

            for record in data.get("results", []):
                fields = record.get("record", {}).get("fields", record)
                if isinstance(fields, dict):
                    tender_id = fields.get("idweb", fields.get("id", ""))
                    tender = Tender(
                        id=f"BOAMP-{tender_id}",
                        title=fields.get("objet", "Sans titre"),
                        source="BOAMP",
                        url=f"https://www.boamp.fr/avis/detail/{tender_id}",
                        publication_date=fields.get("dateparution", ""),
                        deadline=fields.get("datelimitereponse", ""),
                        description=fields.get("descripteur", fields.get("objet", "")),
                        buyer=fields.get("nomacheteur", ""),
                        cpv_codes=_extract_cpv(fields),
                        amount_estimate=str(fields.get("montant", "")),
                        location=fields.get("departement", ""),
                        raw_data=fields,
                    )
                    tenders.append(tender)

            logger.info(f"BOAMP: {len(tenders)} appels d'offres trouvés")

    except httpx.HTTPError as e:
        logger.error(f"Erreur BOAMP API: {e}")
    except Exception as e:
        logger.error(f"Erreur inattendue BOAMP: {e}")

    return tenders


async def scrape_place(days_back: int = 7) -> list[Tender]:
    """
    Récupère les appels d'offres depuis la PLACE (marches-publics.gouv.fr) via flux RSS.
    """
    tenders = []
    rss_url = "https://www.marches-publics.gouv.fr/app/es/syndication/flux-rss"

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(rss_url)
            resp.raise_for_status()
            feed = feedparser.parse(resp.text)

            for entry in feed.entries:
                title_lower = entry.get("title", "").lower()
                summary_lower = entry.get("summary", "").lower()
                combined = f"{title_lower} {summary_lower}"

                # Filtrer les AO liés à la formation
                if any(kw in combined for kw in KEYWORDS_FORMATION):
                    entry_id = hashlib.md5(entry.get("link", "").encode()).hexdigest()[:12]
                    tender = Tender(
                        id=f"PLACE-{entry_id}",
                        title=entry.get("title", "Sans titre"),
                        source="PLACE",
                        url=entry.get("link", ""),
                        publication_date=entry.get("published", ""),
                        deadline=_extract_deadline_from_rss(entry),
                        description=entry.get("summary", ""),
                        buyer=entry.get("author", ""),
                        raw_data=dict(entry),
                    )
                    tenders.append(tender)

            logger.info(f"PLACE: {len(tenders)} appels d'offres trouvés")

    except Exception as e:
        logger.error(f"Erreur PLACE RSS: {e}")

    return tenders


async def scrape_ted(days_back: int = 7) -> list[Tender]:
    """
    Récupère les appels d'offres depuis TED (Tenders Electronic Daily) - marchés européens.
    Filtre par codes CPV formation et pays France.
    """
    tenders = []
    ted_url = os.getenv("TED_API_URL", "https://ted.europa.eu/api/v3.0")

    cpv_filter = " OR ".join(f"cpv:{code}" for code in CPV_FORMATION[:5])
    date_from = (datetime.now() - timedelta(days=days_back)).strftime("%Y%m%d")

    params = {
        "q": f"({cpv_filter}) AND TD:3 AND CY:FR",
        "scope": 3,
        "fields": "ND,TI,CY,DD,DT,OL,AC,RC",
        "size": 30,
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{ted_url}/notices/search", params=params)
            resp.raise_for_status()
            data = resp.json()

            for notice in data.get("results", []):
                tender = Tender(
                    id=f"TED-{notice.get('ND', '')}",
                    title=notice.get("TI", {}).get("FR", "Sans titre"),
                    source="TED",
                    url=f"https://ted.europa.eu/notice/{notice.get('ND', '')}",
                    publication_date=notice.get("DD", ""),
                    deadline=notice.get("DT", ""),
                    description=str(notice.get("AC", "")),
                    buyer=str(notice.get("AC", "")),
                    location="France",
                    raw_data=notice,
                )
                tenders.append(tender)

            logger.info(f"TED: {len(tenders)} appels d'offres trouvés")

    except Exception as e:
        logger.error(f"Erreur TED API: {e}")

    return tenders


async def scrape_all_sources(days_back: int = 7) -> list[Tender]:
    """Lance le scraping sur toutes les sources et déduplique."""
    import asyncio

    results = await asyncio.gather(
        scrape_boamp(days_back),
        scrape_place(days_back),
        scrape_ted(days_back),
        return_exceptions=True,
    )

    all_tenders = []
    for result in results:
        if isinstance(result, list):
            all_tenders.extend(result)
        elif isinstance(result, Exception):
            logger.error(f"Erreur lors du scraping: {result}")

    # Dédupliquer par titre similaire
    seen_titles = set()
    unique_tenders = []
    for t in all_tenders:
        title_key = t.title.lower().strip()[:80]
        if title_key not in seen_titles:
            seen_titles.add(title_key)
            unique_tenders.append(t)

    logger.info(f"Total: {len(unique_tenders)} appels d'offres uniques trouvés")
    return unique_tenders


def _extract_cpv(fields: dict) -> list[str]:
    """Extrait les codes CPV d'un enregistrement BOAMP."""
    cpv = fields.get("cpv", "")
    if isinstance(cpv, str):
        return [c.strip() for c in cpv.split(",") if c.strip()]
    if isinstance(cpv, list):
        return cpv
    return []


def _extract_deadline_from_rss(entry: dict) -> str:
    """Tente d'extraire la date limite depuis un flux RSS."""
    for key in ("deadline", "datelimite", "expiry"):
        if key in entry:
            return str(entry[key])
    return ""
