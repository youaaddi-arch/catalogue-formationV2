"""Module d'extraction de la date de début de contrat depuis les CERFA PDF."""

import io
import logging
import os
import re
from typing import Optional

logger = logging.getLogger(__name__)

# Patterns pour trouver la date de début d'exécution du contrat dans le CERFA
DATE_PATTERNS = [
    # "Date de début d'exécution du contrat : 13/02/2024"
    re.compile(
        r"[Dd]ate\s+de\s+d[ée]but\s+d['']?ex[ée]cution\s+du\s+contrat\s*[:\-]?\s*"
        r"(\d{2}[/\.\-]\d{2}[/\.\-]\d{4})"
    ),
    # "Début d'exécution du contrat : 13/02/2024"
    re.compile(
        r"[Dd][ée]but\s+d['']?ex[ée]cution\s+du\s+contrat\s*[:\-]?\s*"
        r"(\d{2}[/\.\-]\d{2}[/\.\-]\d{4})"
    ),
    # "Date de début d'exécution du" suivi de "contrat :" sur la ligne suivante
    re.compile(
        r"[Dd]ate\s+de\s+d[ée]but\s+d['']?ex[ée]cution\s+du\s*\n?\s*contrat\s*[:\-]?\s*"
        r"(\d{2}[/\.\-]\d{2}[/\.\-]\d{4})",
        re.MULTILINE,
    ),
    # Pattern plus souple : "contrat" suivi d'une date sur la même ligne ou la suivante
    re.compile(
        r"contrat\s*[:\-]?\s*\n?\s*(\d{2}[/\.\-]\d{2}[/\.\-]\d{4})",
        re.IGNORECASE | re.MULTILINE,
    ),
    # "Date d'embauche : 13/02/2024"
    re.compile(
        r"[Dd]ate\s+d['']?embauche\s*[:\-]?\s*(\d{2}[/\.\-]\d{2}[/\.\-]\d{4})"
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
        logger.warning("pdfplumber non installé, impossible de lire les PDF CERFA")
        return None

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            texte_complet = ""
            for page in pdf.pages:
                texte = page.extract_text()
                if texte:
                    texte_complet += texte + "\n"

            if not texte_complet:
                logger.debug("Aucun texte extrait du PDF CERFA")
                return None

            # Chercher la date avec chaque pattern
            for pattern in DATE_PATTERNS:
                match = pattern.search(texte_complet)
                if match:
                    date = _normaliser_date(match.group(1))
                    logger.info(f"Date de début de contrat extraite du CERFA: {date}")
                    return date

            logger.debug("Date de début de contrat non trouvée dans le CERFA")
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
        return None

    try:
        with open(chemin, "rb") as f:
            return extraire_date_contrat_depuis_pdf(f.read())
    except Exception as e:
        logger.error(f"Erreur lecture fichier CERFA {chemin}: {e}")
        return None
