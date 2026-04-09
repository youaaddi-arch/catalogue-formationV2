#!/usr/bin/env python3
"""
Script : liste TOUS les dossiers d'apprentis sur le Drive,
entre dans chaque dossier, trouve le CERFA, le télécharge,
extrait la date de début de contrat, génère l'Excel.

Usage:
    cd ~/Desktop/catalogue-formationV2/opco-completude
    python3 telecharger_cerfas.py
"""

import io
import logging
import os
import re
import sys
import unicodedata
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).parent
CERFAS_DIR = SCRIPT_DIR / "cerfas"
CREDENTIALS_PATH = SCRIPT_DIR / "credentials.json"

sys.path.insert(0, str(SCRIPT_DIR))
from config import APPRENTIS, DRIVE_CIBLE_ID, DRIVE_SOURCE_ID, DOSSIERS_APPRENANTS


def normaliser(nom):
    nom = unicodedata.normalize("NFD", nom)
    nom = "".join(c for c in nom if unicodedata.category(c) != "Mn")
    nom = nom.lower()
    nom = re.sub(r"[-_'\".,]", " ", nom)
    nom = re.sub(r"\s+", " ", nom).strip()
    return nom


def mots_de(nom):
    return {m for m in normaliser(nom).split() if len(m) > 1}


def _escape(text):
    return text.replace("\\", "\\\\").replace("'", "\\'")


# =============================================================================
# CONNEXION
# =============================================================================

def connecter_drive():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    if not CREDENTIALS_PATH.exists():
        print(f"ERREUR: credentials.json introuvable dans {SCRIPT_DIR}")
        sys.exit(1)

    credentials = service_account.Credentials.from_service_account_file(
        str(CREDENTIALS_PATH),
        scopes=["https://www.googleapis.com/auth/drive.readonly"],
    )
    service = build("drive", "v3", credentials=credentials)
    print("Connexion Google Drive OK\n")
    return service


# =============================================================================
# LISTER LES DOSSIERS ET FICHIERS
# =============================================================================

def lister_sous_dossiers(service, parent_id):
    """Liste tous les sous-dossiers d'un dossier."""
    q = f"'{parent_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    return _api_list(service, q)


def lister_fichiers(service, parent_id):
    """Liste tous les fichiers (non-dossiers) d'un dossier."""
    q = f"'{parent_id}' in parents and mimeType != 'application/vnd.google-apps.folder' and trashed = false"
    return _api_list(service, q)


def _api_list(service, query):
    all_files = []
    page_token = None
    try:
        while True:
            params = {
                "q": query,
                "pageSize": 1000,
                "fields": "nextPageToken, files(id, name, mimeType, webViewLink)",
                "supportsAllDrives": True,
                "includeItemsFromAllDrives": True,
            }
            if page_token:
                params["pageToken"] = page_token
            results = service.files().list(**params).execute()
            all_files.extend(results.get("files", []))
            page_token = results.get("nextPageToken")
            if not page_token:
                break
    except Exception as e:
        logger.debug(f"API: {e}")
    return all_files


# =============================================================================
# TROUVER TOUS LES DOSSIERS D'APPRENTIS
# =============================================================================

def trouver_tous_dossiers_apprentis(service):
    """
    Parcourt le Drive CIBLE > Dossiers apprenants > sous-dossiers.
    Retourne un dict {nom_dossier: {id, name, fichiers}}.
    """
    print("Scan du Drive CIBLE (Contrôle OPCO EP)...")
    dossiers = {}

    # Lister la racine du Drive CIBLE
    racine = lister_sous_dossiers(service, DRIVE_CIBLE_ID)
    print(f"  Racine: {len(racine)} dossiers")

    for dossier in racine:
        nom = dossier["name"]
        # Chercher les dossiers "Dossiers apprenants", "PARTIE 2...", etc.
        is_apprenants = any(
            da.lower() in nom.lower() for da in DOSSIERS_APPRENANTS
        ) or "apprenants" in nom.lower()

        if is_apprenants:
            print(f"  -> Scan de '{nom}'...")
            sous_dossiers = lister_sous_dossiers(service, dossier["id"])
            for sd in sous_dossiers:
                dossiers[sd["name"]] = {
                    "id": sd["id"],
                    "name": sd["name"],
                }
            print(f"     {len(sous_dossiers)} dossiers d'apprentis")

    print(f"\nTotal: {len(dossiers)} dossiers d'apprentis trouvés sur le Drive")
    return dossiers


def associer_apprenti_dossier(nom_apprenti, dossiers):
    """Trouve le meilleur dossier pour un apprenti par fuzzy matching."""
    mots_apprenti = mots_de(nom_apprenti)
    if not mots_apprenti:
        return None

    meilleur = None
    meilleur_score = 0

    for nom_dossier, info in dossiers.items():
        mots_dossier = mots_de(nom_dossier)
        if not mots_dossier:
            continue

        # Compter les mots en commun
        communs = mots_apprenti & mots_dossier
        if not communs:
            continue

        # Score = proportion de mots de l'apprenti trouvés dans le dossier
        score = len(communs) / len(mots_apprenti)

        # Au moins 2 mots en commun (ou tous si nom court)
        seuil_mots = min(2, len(mots_apprenti))
        if len(communs) >= seuil_mots and score > meilleur_score:
            meilleur_score = score
            meilleur = info

    return meilleur


# =============================================================================
# CERFA DETECTION
# =============================================================================

CERFA_MOTS_CLES = ["cerfa", "contrat apprentissage", "contrat_apprentissage",
                    "fa13", "fa 13", "ej20", "ej 20"]


def est_cerfa(nom_fichier):
    nom_lower = normaliser(nom_fichier)
    return any(mot in nom_lower for mot in CERFA_MOTS_CLES)


# =============================================================================
# TÉLÉCHARGEMENT
# =============================================================================

def telecharger(service, file_id):
    from googleapiclient.http import MediaIoBaseDownload

    try:
        meta = service.files().get(
            fileId=file_id, fields="mimeType", supportsAllDrives=True
        ).execute()
        mime = meta.get("mimeType", "")

        if mime.startswith("application/vnd.google-apps."):
            req = service.files().export_media(fileId=file_id, mimeType="application/pdf")
        else:
            req = service.files().get_media(fileId=file_id, supportsAllDrives=True)

        buf = io.BytesIO()
        dl = MediaIoBaseDownload(buf, req)
        done = False
        while not done:
            _, done = dl.next_chunk()
        return buf.getvalue()

    except Exception as e:
        logger.error(f"  Téléchargement échoué: {e}")
        return None


# =============================================================================
# EXTRACTION DATE
# =============================================================================

DATE_PATTERNS = [
    re.compile(
        r"[Dd]ate\s+de\s+d[ée]but\s+d['\u2019]?\s*ex[ée]cution\s+du\s+contrat\s*[:\-]?\s*"
        r"(\d{2}[/\.\-]\d{2}[/\.\-]\d{4})"
    ),
    re.compile(
        r"[Dd]ate\s+de\s+d[ée]but\s+d['\u2019]?\s*ex[ée]cution\s+du\s*\n?\s*"
        r"contrat\s*[:\-]?\s*\n?\s*(\d{2}[/\.\-]\d{2}[/\.\-]\d{4})",
        re.MULTILINE,
    ),
    re.compile(
        r"d[ée]but\s+d['\u2019]?\s*ex[ée]cution\s+du\s*\n?\s*contrat\s*[:\-]?\s*\n?\s*"
        r"(\d{2}[/\.\-]\d{2}[/\.\-]\d{4})",
        re.IGNORECASE | re.MULTILINE,
    ),
    re.compile(
        r"ex[ée]cution\s+du\s*\n?\s*contrat\s*[:\-]?\s*\n?\s*(\d{2}[/\.\-]\d{2}[/\.\-]\d{4})",
        re.IGNORECASE | re.MULTILINE,
    ),
    re.compile(
        r"[Dd]ate\s+d['\u2019]?\s*embauche\s*[:\-]?\s*(\d{2}[/\.\-]\d{2}[/\.\-]\d{4})"
    ),
    re.compile(
        r"contrat\s*[:\-]\s*\n?\s*(\d{2}[/\.\-]\d{2}[/\.\-]\d{4})",
        re.IGNORECASE | re.MULTILINE,
    ),
]


def extraire_date(pdf_bytes):
    import pdfplumber

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            texte = ""
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    texte += t + "\n"

            if not texte:
                return None, "PDF vide ou image scannée"

            for pattern in DATE_PATTERNS:
                match = pattern.search(texte)
                if match:
                    date = match.group(1).replace("-", "/").replace(".", "/")
                    return date, None

            return None, texte[:300]

    except Exception as e:
        return None, str(e)


# =============================================================================
# MAIN
# =============================================================================

def main():
    print()
    print("=" * 60)
    print("  EXTRACTION DES DATES DE CONTRAT DEPUIS LES CERFAS")
    print("=" * 60)
    print()

    CERFAS_DIR.mkdir(exist_ok=True)
    service = connecter_drive()

    # ÉTAPE 1 : Lister TOUS les dossiers d'apprentis sur le Drive
    dossiers = trouver_tous_dossiers_apprentis(service)

    if not dossiers:
        print("\nERREUR: Aucun dossier d'apprenti trouvé sur le Drive !")
        print("Vérifiez que le credentials.json a accès au Drive CIBLE.")
        sys.exit(1)

    # ÉTAPE 2 : Pour chaque apprenti, trouver son dossier et son CERFA
    resultats = []
    nb_cerfas = 0
    nb_dates = 0
    total = len(APPRENTIS)

    print(f"\nTraitement de {total} apprentis...\n")

    for i, nom in enumerate(APPRENTIS):
        print(f"[{i+1}/{total}] {nom}")

        # Trouver le dossier de cet apprenti
        dossier = associer_apprenti_dossier(nom, dossiers)
        if not dossier:
            print(f"  -> Pas de dossier trouvé")
            resultats.append({
                "Nom": nom,
                "Date début contrat (CERFA)": "",
                "Fichier CERFA": "",
                "Dossier Drive": "Non trouvé",
            })
            continue

        print(f"  -> Dossier: {dossier['name']}")

        # Lister les fichiers du dossier
        fichiers = lister_fichiers(service, dossier["id"])
        print(f"  -> {len(fichiers)} fichiers")

        # Trouver le CERFA
        cerfa = None
        for f in fichiers:
            if est_cerfa(f["name"]):
                cerfa = f
                break

        if not cerfa:
            # Chercher aussi dans les sous-dossiers
            sous_dossiers = lister_sous_dossiers(service, dossier["id"])
            for sd in sous_dossiers:
                fichiers_sd = lister_fichiers(service, sd["id"])
                for f in fichiers_sd:
                    if est_cerfa(f["name"]):
                        cerfa = f
                        break
                if cerfa:
                    break

        if not cerfa:
            print(f"  -> PAS DE CERFA")
            noms_fichiers = [f["name"] for f in fichiers[:5]]
            resultats.append({
                "Nom": nom,
                "Date début contrat (CERFA)": "",
                "Fichier CERFA": "Non trouvé",
                "Dossier Drive": dossier["name"],
            })
            continue

        nb_cerfas += 1
        print(f"  -> CERFA: {cerfa['name']}")

        # Télécharger
        pdf_bytes = telecharger(service, cerfa["id"])
        if not pdf_bytes:
            resultats.append({
                "Nom": nom,
                "Date début contrat (CERFA)": "",
                "Fichier CERFA": cerfa["name"],
                "Dossier Drive": dossier["name"],
            })
            continue

        # Sauvegarder
        safe = re.sub(r'[^\w\s\-.]', '_', f"{nom} - {cerfa['name']}")
        (CERFAS_DIR / safe).write_bytes(pdf_bytes)

        # Extraire la date
        date, erreur = extraire_date(pdf_bytes)
        if date:
            nb_dates += 1
            print(f"  -> DATE: {date}")
        else:
            print(f"  -> Date non trouvée")
            if erreur:
                print(f"     Texte: {erreur[:120]}")

        resultats.append({
            "Nom": nom,
            "Date début contrat (CERFA)": date or "",
            "Fichier CERFA": cerfa["name"],
            "Dossier Drive": dossier["name"],
        })

    # ÉTAPE 3 : Générer l'Excel
    import pandas as pd

    df = pd.DataFrame(resultats)
    output = SCRIPT_DIR / "dates_debut_contrat_cerfas.xlsx"

    with pd.ExcelWriter(str(output), engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Dates contrats CERFA")
        ws = writer.sheets["Dates contrats CERFA"]
        for col_idx, col in enumerate(df.columns, 1):
            max_len = max(df[col].astype(str).str.len().max(), len(col))
            ws.column_dimensions[
                ws.cell(row=1, column=col_idx).column_letter
            ].width = min(max_len + 4, 60)

    print()
    print("=" * 60)
    print(f"  {total} apprentis")
    print(f"  {nb_cerfas} CERFAs trouvés")
    print(f"  {nb_dates} dates extraites")
    print()
    print(f"  Excel: {output}")
    print(f"  CERFAs: {CERFAS_DIR}")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
