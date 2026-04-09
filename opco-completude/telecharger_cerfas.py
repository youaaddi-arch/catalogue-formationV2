#!/usr/bin/env python3
"""
Script autonome : télécharge tous les CERFAs depuis Google Drive,
extrait la date de début d'exécution du contrat de chaque PDF,
et génère un fichier Excel avec les résultats.

Usage:
    cd ~/Desktop/catalogue-formationV2/opco-completude
    pip3 install pdfplumber google-api-python-client google-auth pandas openpyxl
    python3 telecharger_cerfas.py
"""

import io
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# --- Config logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# --- Répertoire de travail ---
SCRIPT_DIR = Path(__file__).parent
CERFAS_DIR = SCRIPT_DIR / "cerfas"
CREDENTIALS_PATH = SCRIPT_DIR / "credentials.json"

# --- Liste des apprentis (depuis config.py) ---
sys.path.insert(0, str(SCRIPT_DIR))
from config import APPRENTIS

# =============================================================================
# 1. CONNEXION GOOGLE DRIVE
# =============================================================================

def connecter_drive():
    """Se connecte au Google Drive avec le credentials.json."""
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    if not CREDENTIALS_PATH.exists():
        logger.error(f"credentials.json introuvable dans {SCRIPT_DIR}")
        logger.error("Place ton fichier credentials.json dans le dossier opco-completude/")
        sys.exit(1)

    credentials = service_account.Credentials.from_service_account_file(
        str(CREDENTIALS_PATH),
        scopes=["https://www.googleapis.com/auth/drive.readonly"],
    )
    service = build("drive", "v3", credentials=credentials)
    logger.info("Connexion Google Drive OK")
    return service


# =============================================================================
# 2. RECHERCHE ET TÉLÉCHARGEMENT DES CERFAS
# =============================================================================

def chercher_cerfas(service):
    """Cherche tous les fichiers CERFA sur le Drive."""
    logger.info("Recherche des fichiers CERFA sur le Drive...")

    # Chercher par mot-clé "cerfa"
    query = (
        "name contains 'cerfa' "
        "and mimeType != 'application/vnd.google-apps.folder' "
        "and trashed = false"
    )

    all_files = []
    page_token = None

    while True:
        params = {
            "q": query,
            "pageSize": 1000,
            "fields": "nextPageToken, files(id, name, mimeType, parents, webViewLink)",
            "supportsAllDrives": True,
            "includeItemsFromAllDrives": True,
            "corpora": "allDrives",
        }
        if page_token:
            params["pageToken"] = page_token

        results = service.files().list(**params).execute()
        files = results.get("files", [])
        all_files.extend(files)

        page_token = results.get("nextPageToken")
        if not page_token:
            break

    # Chercher aussi "contrat apprentissage"
    query2 = (
        "name contains 'contrat' "
        "and mimeType != 'application/vnd.google-apps.folder' "
        "and trashed = false"
    )
    page_token = None
    while True:
        params = {
            "q": query2,
            "pageSize": 1000,
            "fields": "nextPageToken, files(id, name, mimeType, parents, webViewLink)",
            "supportsAllDrives": True,
            "includeItemsFromAllDrives": True,
            "corpora": "allDrives",
        }
        if page_token:
            params["pageToken"] = page_token
        results = service.files().list(**params).execute()
        files = results.get("files", [])
        # Ne pas dupliquer
        ids_existants = {f["id"] for f in all_files}
        for f in files:
            if f["id"] not in ids_existants:
                all_files.append(f)
        page_token = results.get("nextPageToken")
        if not page_token:
            break

    logger.info(f"Trouvé {len(all_files)} fichiers CERFA/contrat sur le Drive")
    return all_files


def telecharger_fichier(service, file_id, file_name):
    """Télécharge un fichier depuis Google Drive."""
    from googleapiclient.http import MediaIoBaseDownload

    try:
        # Vérifier le type
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
        logger.error(f"Erreur téléchargement {file_name}: {e}")
        return None


def trouver_nom_parent(service, file_info):
    """Récupère le nom du dossier parent d'un fichier."""
    parents = file_info.get("parents", [])
    if not parents:
        return ""
    try:
        parent = service.files().get(
            fileId=parents[0], fields="name", supportsAllDrives=True
        ).execute()
        return parent.get("name", "")
    except Exception:
        return ""


# =============================================================================
# 3. EXTRACTION DE LA DATE DEPUIS LE PDF
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
    """Extrait la date de début de contrat depuis un PDF."""
    try:
        import pdfplumber
    except ImportError:
        logger.error("pdfplumber non installé ! Lance: pip3 install pdfplumber")
        return None

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            texte = ""
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    texte += t + "\n"

            if not texte:
                return None

            for pattern in DATE_PATTERNS:
                match = pattern.search(texte)
                if match:
                    date = match.group(1).replace("-", "/").replace(".", "/")
                    return date

            return None
    except Exception as e:
        logger.error(f"Erreur lecture PDF: {e}")
        return None


# =============================================================================
# 4. ASSOCIATION CERFA <-> APPRENTI
# =============================================================================

def normaliser(nom):
    """Normalise un nom pour comparaison."""
    import unicodedata
    nom = unicodedata.normalize("NFD", nom)
    nom = "".join(c for c in nom if unicodedata.category(c) != "Mn")
    nom = nom.lower()
    nom = re.sub(r"[-_'\".,]", " ", nom)
    nom = re.sub(r"\s+", " ", nom).strip()
    return nom


def mots_nom(nom):
    """Extrait les mots significatifs d'un nom."""
    return {m for m in normaliser(nom).split() if len(m) > 1}


def associer_cerfa_apprenti(nom_fichier, dossier_parent, apprentis):
    """Trouve l'apprenti correspondant à un fichier CERFA."""
    texte = normaliser(nom_fichier + " " + dossier_parent)

    meilleur = None
    meilleur_score = 0

    for nom in apprentis:
        mots = mots_nom(nom)
        if not mots:
            continue
        trouves = sum(1 for m in mots if m in texte)
        score = trouves / len(mots)
        if score > meilleur_score and trouves >= min(2, len(mots)):
            meilleur_score = score
            meilleur = nom

    return meilleur


# =============================================================================
# 5. SCRIPT PRINCIPAL
# =============================================================================

def main():
    print("=" * 60)
    print("  EXTRACTION DES DATES DE DÉBUT DE CONTRAT DEPUIS LES CERFAS")
    print("=" * 60)
    print()

    # Créer le dossier cerfas/
    CERFAS_DIR.mkdir(exist_ok=True)

    # Connexion Drive
    service = connecter_drive()

    # Chercher les CERFAs
    fichiers_cerfa = chercher_cerfas(service)

    if not fichiers_cerfa:
        logger.error("Aucun fichier CERFA trouvé sur le Drive !")
        sys.exit(1)

    # Télécharger et analyser chaque CERFA
    resultats = {}  # nom_apprenti -> {date, fichier}

    for i, fichier in enumerate(fichiers_cerfa):
        nom = fichier["name"]
        file_id = fichier["id"]
        logger.info(f"[{i+1}/{len(fichiers_cerfa)}] {nom}")

        # Trouver le dossier parent
        parent = trouver_nom_parent(service, fichier)

        # Associer à un apprenti
        apprenti = associer_cerfa_apprenti(nom, parent, APPRENTIS)
        if not apprenti:
            logger.warning(f"  -> Pas d'apprenti associé, ignoré")
            continue

        logger.info(f"  -> Apprenti: {apprenti}")

        # Télécharger le fichier
        pdf_bytes = telecharger_fichier(service, file_id, nom)
        if not pdf_bytes:
            logger.warning(f"  -> Échec téléchargement")
            continue

        # Sauvegarder dans cerfas/
        safe_name = re.sub(r'[^\w\s\-.]', '_', nom)
        dest = CERFAS_DIR / safe_name
        dest.write_bytes(pdf_bytes)
        logger.info(f"  -> Sauvegardé: {dest.name}")

        # Extraire la date
        date = extraire_date_pdf(pdf_bytes)
        if date:
            logger.info(f"  -> DATE DÉBUT CONTRAT: {date}")
            resultats[apprenti] = {
                "date_debut_contrat": date,
                "fichier_cerfa": nom,
                "dossier_parent": parent,
            }
        else:
            logger.warning(f"  -> Date non trouvée dans le PDF")
            resultats.setdefault(apprenti, {
                "date_debut_contrat": "",
                "fichier_cerfa": nom,
                "dossier_parent": parent,
            })

    # Générer l'Excel
    print()
    print("=" * 60)
    print("  GÉNÉRATION DU FICHIER EXCEL")
    print("=" * 60)

    import pandas as pd

    rows = []
    for nom in APPRENTIS:
        info = resultats.get(nom, {})
        rows.append({
            "Nom": nom,
            "Date début contrat (CERFA)": info.get("date_debut_contrat", ""),
            "Fichier CERFA": info.get("fichier_cerfa", "Non trouvé"),
            "Dossier parent": info.get("dossier_parent", ""),
        })

    df = pd.DataFrame(rows)

    # Stats
    nb_dates = sum(1 for r in rows if r["Date début contrat (CERFA)"])
    nb_cerfas = sum(1 for r in rows if r["Fichier CERFA"] != "Non trouvé")

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
    print(f"  RÉSULTAT:")
    print(f"  - {len(APPRENTIS)} apprentis")
    print(f"  - {nb_cerfas} CERFAs trouvés")
    print(f"  - {nb_dates} dates extraites")
    print()
    print(f"  Fichier Excel: {output_path}")
    print(f"  Dossier CERFAs: {CERFAS_DIR}")
    print()
    print("=" * 60)


if __name__ == "__main__":
    main()
