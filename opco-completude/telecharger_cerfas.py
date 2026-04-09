#!/usr/bin/env python3
"""
Script autonome : pour chaque apprenti, cherche son CERFA sur Google Drive,
le télécharge, extrait la date de début d'exécution du contrat,
et génère un fichier Excel avec les résultats.

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
from datetime import datetime
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
from config import APPRENTIS


# =============================================================================
# UTILITAIRES
# =============================================================================

def normaliser(nom):
    nom = unicodedata.normalize("NFD", nom)
    nom = "".join(c for c in nom if unicodedata.category(c) != "Mn")
    nom = nom.lower()
    nom = re.sub(r"[-_'\".,]", " ", nom)
    nom = re.sub(r"\s+", " ", nom).strip()
    return nom


# =============================================================================
# CONNEXION GOOGLE DRIVE
# =============================================================================

def connecter_drive():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    if not CREDENTIALS_PATH.exists():
        logger.error(f"credentials.json introuvable dans {SCRIPT_DIR}")
        sys.exit(1)

    credentials = service_account.Credentials.from_service_account_file(
        str(CREDENTIALS_PATH),
        scopes=["https://www.googleapis.com/auth/drive.readonly"],
    )
    service = build("drive", "v3", credentials=credentials)
    logger.info("Connexion Google Drive OK")
    return service


# =============================================================================
# CHERCHER LES FICHIERS D'UN APPRENTI SUR LE DRIVE
# =============================================================================

def chercher_fichiers_apprenti(service, nom_apprenti):
    """Cherche tous les fichiers d'un apprenti sur le Drive."""
    # Prendre les 2 premiers mots significatifs du nom
    mots = [m for m in nom_apprenti.split() if len(m) > 1]
    if not mots:
        return []

    mots_recherche = mots[:2]

    tous_fichiers = []
    noms_vus = set()

    # 1. Chercher les DOSSIERS qui contiennent le nom de l'apprenti
    query_parts = [f"name contains '{_escape(m)}'" for m in mots_recherche]
    query = (
        f"mimeType = 'application/vnd.google-apps.folder' "
        f"and {' and '.join(query_parts)} and trashed = false"
    )
    dossiers = _list_files(service, query)

    # Lister le contenu de chaque dossier trouvé
    for dossier in dossiers:
        fichiers = _list_folder_files(service, dossier["id"])
        for f in fichiers:
            if f["name"] not in noms_vus:
                noms_vus.add(f["name"])
                tous_fichiers.append(f)

    # 2. Chercher les FICHIERS qui contiennent le nom directement
    query = (
        f"mimeType != 'application/vnd.google-apps.folder' "
        f"and {' and '.join(query_parts)} and trashed = false"
    )
    fichiers_directs = _list_files(service, query)
    for f in fichiers_directs:
        if f["name"] not in noms_vus:
            noms_vus.add(f["name"])
            tous_fichiers.append(f)

    return tous_fichiers


def trouver_cerfa(fichiers):
    """Parmi une liste de fichiers, trouve le CERFA."""
    mots_cles = ["cerfa", "contrat apprentissage", "contrat_apprentissage",
                  "fa13", "fa 13", "ej20", "ej 20"]
    for f in fichiers:
        nom_lower = normaliser(f["name"])
        for mot in mots_cles:
            if mot in nom_lower:
                return f
    return None


def _escape(text):
    return text.replace("\\", "\\\\").replace("'", "\\'")


def _list_files(service, query):
    all_files = []
    page_token = None
    try:
        while True:
            params = {
                "q": query,
                "pageSize": 200,
                "fields": "nextPageToken, files(id, name, mimeType, parents, webViewLink)",
                "supportsAllDrives": True,
                "includeItemsFromAllDrives": True,
                "corpora": "allDrives",
            }
            if page_token:
                params["pageToken"] = page_token
            results = service.files().list(**params).execute()
            all_files.extend(results.get("files", []))
            page_token = results.get("nextPageToken")
            if not page_token:
                break
    except Exception as e:
        logger.debug(f"Erreur API: {e}")
    return all_files


def _list_folder_files(service, folder_id):
    q = f"'{folder_id}' in parents and trashed = false"
    try:
        params = {
            "q": q,
            "pageSize": 200,
            "fields": "nextPageToken, files(id, name, mimeType, webViewLink)",
            "supportsAllDrives": True,
            "includeItemsFromAllDrives": True,
        }
        results = service.files().list(**params).execute()
        return results.get("files", [])
    except Exception:
        return []


# =============================================================================
# TÉLÉCHARGEMENT PDF
# =============================================================================

def telecharger_fichier(service, file_id, file_name):
    from googleapiclient.http import MediaIoBaseDownload

    try:
        file_meta = service.files().get(
            fileId=file_id, fields="mimeType", supportsAllDrives=True
        ).execute()
        mime = file_meta.get("mimeType", "")

        if mime.startswith("application/vnd.google-apps."):
            request = service.files().export_media(
                fileId=file_id, mimeType="application/pdf"
            )
        else:
            request = service.files().get_media(
                fileId=file_id, supportsAllDrives=True
            )

        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()

        return buffer.getvalue()

    except Exception as e:
        logger.error(f"  Erreur téléchargement {file_name}: {e}")
        return None


# =============================================================================
# EXTRACTION DATE DEPUIS PDF
# =============================================================================

DATE_PATTERNS = [
    re.compile(
        r"[Dd]ate\s+de\s+d[ée]but\s+d['\u2019\u0027]?\s*ex[ée]cution\s+du\s+contrat\s*[:\-]?\s*"
        r"(\d{2}[/\.\-]\d{2}[/\.\-]\d{4})"
    ),
    re.compile(
        r"[Dd]ate\s+de\s+d[ée]but\s+d['\u2019\u0027]?\s*ex[ée]cution\s+du\s*\n?\s*"
        r"contrat\s*[:\-]?\s*\n?\s*(\d{2}[/\.\-]\d{2}[/\.\-]\d{4})",
        re.MULTILINE,
    ),
    re.compile(
        r"d[ée]but\s+d['\u2019\u0027]?\s*ex[ée]cution\s+du\s*\n?\s*contrat\s*[:\-]?\s*\n?\s*"
        r"(\d{2}[/\.\-]\d{2}[/\.\-]\d{4})",
        re.IGNORECASE | re.MULTILINE,
    ),
    re.compile(
        r"ex[ée]cution\s+du\s*\n?\s*contrat\s*[:\-]?\s*\n?\s*(\d{2}[/\.\-]\d{2}[/\.\-]\d{4})",
        re.IGNORECASE | re.MULTILINE,
    ),
    re.compile(
        r"[Dd]ate\s+d['\u2019\u0027]?\s*embauche\s*[:\-]?\s*(\d{2}[/\.\-]\d{2}[/\.\-]\d{4})"
    ),
    re.compile(
        r"contrat\s*[:\-]\s*\n?\s*(\d{2}[/\.\-]\d{2}[/\.\-]\d{4})",
        re.IGNORECASE | re.MULTILINE,
    ),
]


def extraire_date_pdf(pdf_bytes):
    import pdfplumber

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            texte = ""
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    texte += t + "\n"

            if not texte:
                return None, "PDF vide (image scannée ?)"

            for pattern in DATE_PATTERNS:
                match = pattern.search(texte)
                if match:
                    date = match.group(1).replace("-", "/").replace(".", "/")
                    return date, None

            # Pas trouvé - retourner un extrait du texte pour debug
            return None, texte[:300]

    except Exception as e:
        return None, str(e)


# =============================================================================
# SCRIPT PRINCIPAL
# =============================================================================

def main():
    print()
    print("=" * 60)
    print("  EXTRACTION DES DATES DE CONTRAT DEPUIS LES CERFAS")
    print("=" * 60)
    print()

    CERFAS_DIR.mkdir(exist_ok=True)
    service = connecter_drive()

    resultats = []
    nb_cerfas = 0
    nb_dates = 0

    total = len(APPRENTIS)

    for i, nom in enumerate(APPRENTIS):
        print(f"\n[{i+1}/{total}] {nom}")

        # Chercher les fichiers de cet apprenti
        fichiers = chercher_fichiers_apprenti(service, nom)
        print(f"  -> {len(fichiers)} fichiers trouvés sur le Drive")

        # Trouver le CERFA parmi les fichiers
        cerfa = trouver_cerfa(fichiers)

        if not cerfa:
            print(f"  -> PAS DE CERFA trouvé")
            resultats.append({
                "Nom": nom,
                "Date début contrat (CERFA)": "",
                "Fichier CERFA": "Non trouvé",
                "Remarque": f"{len(fichiers)} fichiers mais aucun CERFA",
            })
            continue

        nb_cerfas += 1
        print(f"  -> CERFA trouvé: {cerfa['name']}")

        # Télécharger le CERFA
        pdf_bytes = telecharger_fichier(service, cerfa["id"], cerfa["name"])
        if not pdf_bytes:
            print(f"  -> ERREUR téléchargement")
            resultats.append({
                "Nom": nom,
                "Date début contrat (CERFA)": "",
                "Fichier CERFA": cerfa["name"],
                "Remarque": "Erreur téléchargement",
            })
            continue

        # Sauvegarder le PDF
        safe_name = re.sub(r'[^\w\s\-.]', '_', f"{nom} - {cerfa['name']}")
        dest = CERFAS_DIR / safe_name
        dest.write_bytes(pdf_bytes)

        # Extraire la date
        date, erreur = extraire_date_pdf(pdf_bytes)
        if date:
            nb_dates += 1
            print(f"  -> DATE DÉBUT CONTRAT: {date}")
            resultats.append({
                "Nom": nom,
                "Date début contrat (CERFA)": date,
                "Fichier CERFA": cerfa["name"],
                "Remarque": "",
            })
        else:
            print(f"  -> Date non trouvée dans le PDF")
            if erreur:
                print(f"     Extrait texte: {erreur[:150]}")
            resultats.append({
                "Nom": nom,
                "Date début contrat (CERFA)": "",
                "Fichier CERFA": cerfa["name"],
                "Remarque": f"Date non trouvée. Texte: {(erreur or '')[:100]}",
            })

    # Générer l'Excel
    import pandas as pd

    df = pd.DataFrame(resultats)

    output_path = SCRIPT_DIR / "dates_debut_contrat_cerfas.xlsx"
    with pd.ExcelWriter(str(output_path), engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Dates contrats CERFA")
        ws = writer.sheets["Dates contrats CERFA"]
        for col_idx, col in enumerate(df.columns, 1):
            max_len = max(df[col].astype(str).str.len().max(), len(col))
            ws.column_dimensions[
                ws.cell(row=1, column=col_idx).column_letter
            ].width = min(max_len + 4, 60)

    print()
    print("=" * 60)
    print(f"  RÉSULTAT:")
    print(f"  - {total} apprentis")
    print(f"  - {nb_cerfas} CERFAs trouvés")
    print(f"  - {nb_dates} dates extraites")
    print()
    print(f"  Fichier Excel: {output_path}")
    print(f"  Dossier CERFAs: {CERFAS_DIR}")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
