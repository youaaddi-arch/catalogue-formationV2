"""Module de lecture du fichier Excel CONSTATS EP."""

import logging
import os

import pandas as pd

import config
from models import DonnéesExcel

logger = logging.getLogger(__name__)

# Mapping des noms de colonnes possibles vers nos noms internes
COLUMN_MAPPINGS = {
    "numero_dossier": [
        "n° dossier", "numero dossier", "n°dossier", "num dossier",
        "numéro dossier", "numéro de dossier", "n° de dossier",
    ],
    "nom": [
        "nom", "apprenant", "nom apprenant", "nom prénom",
        "nom et prénom", "apprenti", "nom apprenti",
    ],
    "statut_dossier": [
        "statut", "statut dossier", "statut du dossier", "état dossier",
    ],
    "csf": ["csf"],
    "factures_assignation": [
        "factures assignation", "facture assignation", "assignation",
    ],
    "controle_urssaf": [
        "contrôle urssaf", "controle urssaf", "urssaf",
    ],
    "rupture": ["rupture"],
    "date_rupture": ["date rupture", "date de rupture"],
    "maintien": ["maintien"],
    "date_fin_maintien": [
        "date fin maintien", "date de fin de maintien", "fin maintien",
    ],
    "date_embauche": [
        "date d'embauche", "date embauche", "date début contrat",
        "date debut contrat", "début contrat", "debut contrat",
        "date contrat", "embauche",
    ],
    "date_debut_formation": [
        "date début formation", "date debut formation", "début formation",
        "debut formation",
    ],
    "date_fin_formation": [
        "date fin formation", "date de fin de formation", "fin formation",
    ],
    "actions_cfa": [
        "actions cfa", "actions cfa à transmettre", "action cfa",
        "actions à transmettre", "a transmettre",
    ],
}

# Colonnes de constats (1 à 5)
CONSTAT_KEYWORDS = ["constat", "observation"]


def _find_column(df: pd.DataFrame, possible_names: list) -> str | None:
    """Trouve le nom réel d'une colonne parmi les noms possibles."""
    cols_lower = {col.strip().lower(): col for col in df.columns}
    for name in possible_names:
        if name.lower() in cols_lower:
            return cols_lower[name.lower()]
    # Recherche partielle
    for name in possible_names:
        for col_lower, col_real in cols_lower.items():
            if name.lower() in col_lower:
                return col_real
    return None


def _find_constat_columns(df: pd.DataFrame) -> list:
    """Trouve les colonnes de constats (1 à 5)."""
    constat_cols = []
    for col in df.columns:
        col_lower = col.strip().lower()
        for keyword in CONSTAT_KEYWORDS:
            if keyword in col_lower:
                constat_cols.append(col)
                break
    return sorted(constat_cols)


def lire_excel(path: str = None) -> dict:
    """
    Lit le fichier Excel CONSTATS EP et retourne un dict
    {nom_normalise: DonnéesExcel}.
    """
    path = path or config.EXCEL_PATH

    if not os.path.exists(path):
        logger.warning(f"Fichier Excel non trouvé: {path}")
        return {}

    try:
        # Essayer de lire toutes les feuilles
        xls = pd.ExcelFile(path)
        logger.info(f"Feuilles trouvées: {xls.sheet_names}")

        # Chercher la feuille la plus pertinente
        df = None
        for sheet_name in xls.sheet_names:
            temp_df = pd.read_excel(path, sheet_name=sheet_name)
            # Chercher une feuille avec une colonne "nom" ou similaire
            nom_col = _find_column(temp_df, COLUMN_MAPPINGS["nom"])
            if nom_col:
                df = temp_df
                logger.info(f"Utilisation de la feuille: {sheet_name}")
                break

        if df is None:
            # Utiliser la première feuille par défaut
            df = pd.read_excel(path, sheet_name=0)
            logger.warning("Aucune feuille avec colonne 'nom' trouvée, "
                         "utilisation de la première feuille")

        # Nettoyer les noms de colonnes
        df.columns = df.columns.astype(str).str.strip()

        # Trouver les colonnes
        col_map = {}
        for key, possible_names in COLUMN_MAPPINGS.items():
            col_map[key] = _find_column(df, possible_names)

        constat_cols = _find_constat_columns(df)

        logger.info(f"Colonnes mappées: {col_map}")
        logger.info(f"Colonnes de constats: {constat_cols}")

        # Construire le dictionnaire
        result = {}
        nom_col = col_map.get("nom")

        if not nom_col:
            logger.error("Impossible de trouver la colonne 'nom' dans le Excel")
            return {}

        for _, row in df.iterrows():
            nom_raw = str(row.get(nom_col, "")).strip()
            if not nom_raw or nom_raw == "nan":
                continue

            donnees = DonnéesExcel()
            donnees.numero_dossier = _safe_str(row, col_map.get("numero_dossier"))
            donnees.statut_dossier = _safe_str(row, col_map.get("statut_dossier"))
            donnees.csf = _safe_str(row, col_map.get("csf"))
            donnees.factures_assignation = _safe_str(
                row, col_map.get("factures_assignation")
            )
            donnees.controle_urssaf = _safe_str(
                row, col_map.get("controle_urssaf")
            )
            donnees.rupture = _safe_str(row, col_map.get("rupture"))
            donnees.date_rupture = _safe_str(row, col_map.get("date_rupture"))
            donnees.maintien = _safe_str(row, col_map.get("maintien"))
            donnees.date_fin_maintien = _safe_str(
                row, col_map.get("date_fin_maintien")
            )
            donnees.date_embauche = _safe_str(
                row, col_map.get("date_embauche")
            )
            donnees.date_debut_formation = _safe_str(
                row, col_map.get("date_debut_formation")
            )
            donnees.date_fin_formation = _safe_str(
                row, col_map.get("date_fin_formation")
            )
            donnees.actions_cfa = _safe_str(row, col_map.get("actions_cfa"))

            # Constats
            for cc in constat_cols:
                val = _safe_str(row, cc)
                if val:
                    donnees.constats.append(val)

            result[nom_raw] = donnees

        logger.info(f"Lu {len(result)} entrées depuis le fichier Excel")
        return result

    except Exception as e:
        logger.error(f"Erreur lecture Excel: {e}")
        return {}


def _safe_str(row, col_name) -> str | None:
    """Extrait une valeur string d'une ligne pandas de manière sûre."""
    if col_name is None:
        return None
    val = row.get(col_name)
    if pd.isna(val):
        return None
    return str(val).strip()
