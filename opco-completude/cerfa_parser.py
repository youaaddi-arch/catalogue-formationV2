"""Module d'extraction de la date de début de contrat depuis les CERFA PDF."""

import io
import logging
import os
import re
from typing import Optional

logger = logging.getLogger(__name__)

# Patterns pour trouver la date de début d'exécution du contrat dans le CERFA
# Ordonnés du plus spécifique au plus générique
DATE_PATTERNS = [
    # "Date de début d'exécution du contrat : 13/02/2024"
    re.compile(
        r"[Dd]ate\s+de\s+d[ée]but\s+d[''\u2019]?ex[ée]cution\s+du\s+contrat\s*[:\-]?\s*"
        r"(\d{2}[/\.\-]\d{2}[/\.\-]\d{4})"
    ),
    # Multi-ligne: "Date de début d'exécution du\ncontrat :\n13/02/2024"
    re.compile(
        r"[Dd]ate\s+de\s+d[ée]but\s+d[''\u2019]?\s*ex[ée]cution\s+du\s*\n?\s*"
        r"contrat\s*[:\-]?\s*\n?\s*(\d{2}[/\.\-]\d{2}[/\.\-]\d{4})",
        re.MULTILINE,
    ),
    # "Début d'exécution du contrat : 13/02/2024"
    re.compile(
        r"[Dd][ée]but\s+d[''\u2019]?\s*ex[ée]cution\s+du\s+contrat\s*[:\-]?\s*"
        r"(\d{2}[/\.\-]\d{2}[/\.\-]\d{4})"
    ),
    # "début d'exécution du\ncontrat :\n13/02/2024" (multi-ligne)
    re.compile(
        r"d[ée]but\s+d[''\u2019]?\s*ex[ée]cution\s+du\s*\n?\s*contrat\s*[:\-]?\s*\n?\s*"
        r"(\d{2}[/\.\-]\d{2}[/\.\-]\d{4})",
        re.IGNORECASE | re.MULTILINE,
    ),
    # "exécution du contrat" suivi d'une date quelques lignes après
    re.compile(
        r"ex[ée]cution\s+du\s*\n?\s*contrat\s*[:\-]?\s*\n?\s*(\d{2}[/\.\-]\d{2}[/\.\-]\d{4})",
        re.IGNORECASE | re.MULTILINE,
    ),
    # "Date d'embauche : 13/02/2024"
    re.compile(
        r"[Dd]ate\s+d[''\u2019]?\s*embauche\s*[:\-]?\s*(\d{2}[/\.\-]\d{2}[/\.\-]\d{4})"
    ),
    # "contrat :" suivi d'une date sur la même ligne ou la suivante
    re.compile(
        r"contrat\s*[:\-]\s*\n?\s*(\d{2}[/\.\-]\d{2}[/\.\-]\d{4})",
        re.IGNORECASE | re.MULTILINE,
    ),
]


def _normaliser_date(date_str: str) -> str:
    """Normalise une date extraite au format dd/mm/yyyy."""
    return date_str.replace("-", "/").replace(".", "/")


def extraire_date_contrat_depuis_pdf(pdf_bytes: bytes) -> Optional[str]:
    """
    Extrait la date de début d'exécution du contrat depuis un PDF CERFA.

    Args:
        pdf_bytes: Contenu binaire du fichier PDF

    Returns:
        La date au format dd/mm/yyyy ou None si non trouvée
    """
    try:
        import pdfplumber
    except ImportError:
        logger.error(
            "pdfplumber non installé ! Installer avec: pip3 install pdfplumber"
        )
        return None

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            texte_complet = ""
            for page in pdf.pages:
                texte = page.extract_text()
                if texte:
                    texte_complet += texte + "\n"

            if not texte_complet:
                logger.warning("Aucun texte extrait du PDF CERFA (PDF image ?)")
                return None

            logger.debug(f"Texte CERFA extrait ({len(texte_complet)} chars)")

            # Chercher la date avec chaque pattern
            for i, pattern in enumerate(DATE_PATTERNS):
                match = pattern.search(texte_complet)
                if match:
                    date = _normaliser_date(match.group(1))
                    logger.info(
                        f"Date début contrat extraite du CERFA: {date} "
                        f"(pattern #{i+1})"
                    )
                    return date

            # Log du texte pour debug si rien trouvé
            logger.warning(
                "Date de début de contrat non trouvée dans le CERFA. "
                "Premiers 500 chars du texte extrait:"
            )
            logger.warning(texte_complet[:500])
            return None

    except Exception as e:
        logger.error(f"Erreur extraction date depuis PDF CERFA: {e}")
        return None


def extraire_date_contrat_depuis_fichier(chemin: str) -> Optional[str]:
    """
    Extrait la date de début de contrat depuis un fichier PDF local.

    Args:
        chemin: Chemin vers le fichier PDF

    Returns:
        La date au format dd/mm/yyyy ou None si non trouvée
    """
    if not os.path.exists(chemin):
        logger.warning(f"Fichier CERFA non trouvé: {chemin}")
        return None

    # Vérifier que c'est un PDF
    if not chemin.lower().endswith(".pdf"):
        logger.debug(f"Fichier CERFA ignoré (pas un PDF): {chemin}")
        return None

    try:
        with open(chemin, "rb") as f:
            return extraire_date_contrat_depuis_pdf(f.read())
    except Exception as e:
        logger.error(f"Erreur lecture fichier CERFA {chemin}: {e}")
        return None
