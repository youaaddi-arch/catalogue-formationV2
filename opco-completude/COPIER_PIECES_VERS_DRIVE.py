#!/usr/bin/env python3
"""
Script autonome : copie toutes les pièces jointes trouvées dans les
dossiers Google Drive de chaque candidat.

Usage : python3 COPIER_PIECES_VERS_DRIVE.py
(lancer depuis le dossier contenant credentials.json)
"""

import io
import os
import re
import sys
import unicodedata

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload

# ── Configuration ──────────────────────────────────────────────────────

CREDENTIALS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "credentials.json")

DRIVE_CIBLE_ID = "15WG9vMQikQ6dSF3BfGJim-QR23osVCAv"   # Contrôle OPCO EP
DRIVE_SOURCE_ID = "1-1p6IihluGtZTCRFEFDmjYsZIpCsPS_2"  # PROMOTIONS PNBS

SCOPES = ["https://www.googleapis.com/auth/drive"]

DOSSIERS_APPRENANTS = [
    "Dossiers apprenants",
    "PARTIE 2 DOSSIERS APPRENANTS",
    "PARTIE 3 DOSSIERS APPRENANTS",
    "PARTIE 4 DOSSIERS APPRENANTS",
]

APPRENTIS = [
    "FERROUDJA OUSMAIL", "LOUKSSI MOUNDHER CHERIET", "MIKEILA ZENDY TAVARES G",
    "HATEM GAIEB", "ORLANE DESRUE", "RIADH LARBI", "IDIR WANDY MAZIT",
    "ABDERRAHMANE DAIMI", "KIYAN ALIM", "ADAM ALIOUI", "DANNYS OKO",
    "SAID HALLAOUI", "MELISSA CHIMINJER", "Effi Juliette Aline Quaglia",
    "ABDOUL KHADRE N'DIAYE", "FARAH BESSID", "WAYANN GEREME", "Alya Grini",
    "Nadjia TOUILEB", "AHLAM SADI HADDAD", "IMEN TARRES", "OUSMAIL FERROUDJA",
    "ZACKARI ARAB", "AICHA TRAORE", "MOUNIA ALEA-NGONGO",
    "DIATOU ROUTRA TRAORE", "KELYAN BRUNO BARBIN", "ILIE BENTAHAR",
    "NAMISSA DIALLO", "ABISSETOU SAVANE", "HASSINA KADDOURI",
    "NARIMENE BENAMMAR", "NOHAILA SAIDI", "ENGIN SUSTAM", "OLIVIER JOUVET",
    "KAHRAMAN KAMIL CORBACI", "IMANE ALIOUI", "GRACIA MACKOUNDOU BANGOURA",
    "AMELIA CHERIEF", "ANIS AMRAOUI", "ZAHIA AMROUNI", "IANICK NUMA",
    "LEA ALBERGHI", "SAOUNATA MOHAMED", "KINGSHIRO AHO GLELE",
    "HANAH SARAH BEKKAR", "CADETSON LEZEAU", "LYNDA KERKOUCH",
    "JEAN-SEBASTIEN REST", "MARWAN CHELGHOUM", "Aya EL OUAZZANI HELIMI",
    "HASSIMI OUDIABY", "JAMES JULES-CLAUDE FREH", "MEHDI BELKADI",
    "MATHIAS THAILLA CENA", "Berfin ALKAN", "MORGAN GUERENGOMBA",
    "CURTIS YANGA MPANDA", "MOHAMED GAYA ASSAM", "ELIAS LAKHDAR I",
    "ILHAM HAMDAOUI", "LYNDA GUETTAS", "Hugo Cohen", "UMUT ASIKAN",
    "LORENZO CHARRON", "HASSINA KADDOURI", "ROUMAISSA BELKAID",
    "Rayan Yayilkan", "MEMOUNA DRAME", "GERMAINE MBONZI", "DIHYA AKLI",
    "CYLIA BEGADI", "EL-MOUATAZ-BELLAH-RAYAN", "EREN CETIN", "IBRAHIMA BAH",
    "SHAINA HAMMAMI", "ANAIS Bourrai", "ELYSA KAOUI", "SAMANTHA DUCROT",
    "JESSICA CHARBONNIER", "LISA YOUSFI", "Mazigha MANSOURI",
    "Hadir Ferchichia", "ARNAUD LANDUWAMBO TE", "Mehmet GENC",
    "COTRONEOCHLOE", "SHAINAZE HADJADJ", "LAYANA GAYE", "LAURICE SYLVA",
    "SHAIMA SAAOUD", "PRICILLA BORGES TAVARES", "YASMINA KHELOUI",
]

MOTS_CLES_PIECES = {
    "cerfa": ["cerfa"],
    "convention": ["convention", "conven", "cf_"],
    "cni": ["cni", "carte identité", "carte identite", "visa", "passeport",
            "passport", "titre séjour", "titre sejour", "tds", "identité",
            "identite", "sejour", "récépissé", "recepisse", "ats", "aps"],
    "planning": ["planning", "calendrier", "emploi du temps", "edt"],
    "emargement": ["émargement", "emargement", "présence", "presence",
                   "feuille de présence", "signature", "appel"],
    "attestation": ["attestation", "matériel", "materiel", "pc",
                    "ordinateur", "equipement", "équipement", "remise"],
    "rupture": ["rupture", "résiliation", "resiliation"],
    "ecf": ["ecf"],
    "devoirs": ["devoir", "qcm", "contrôle", "controle", "sujet"],
}


# ── Helpers ────────────────────────────────────────────────────────────

def normaliser(nom):
    nom = unicodedata.normalize("NFD", nom)
    nom = "".join(c for c in nom if unicodedata.category(c) != "Mn")
    nom = nom.lower()
    nom = re.sub(r"[-_'\".,]", " ", nom)
    nom = re.sub(r"\s+", " ", nom).strip()
    return nom


def mots(nom):
    return {m for m in normaliser(nom).split() if len(m) > 1}


def nom_dans_fichier(nom_apprenti, nom_fichier):
    """Vérifie si le nom de l'apprenti apparait dans le nom du fichier."""
    m = mots(nom_apprenti)
    fn = normaliser(nom_fichier)
    trouves = sum(1 for mot in m if mot in fn)
    return trouves >= min(2, len(m))


def matcher_apprenti(nom_dossier):
    """Trouve l'apprenti correspondant à un nom de dossier Drive."""
    nom_norm = normaliser(nom_dossier)
    meilleur = None
    meilleur_score = 0
    for apprenti in APPRENTIS:
        m_apprenti = mots(apprenti)
        m_dossier = mots(nom_dossier)
        if not m_apprenti or not m_dossier:
            continue
        inter = m_apprenti & m_dossier
        union = m_apprenti | m_dossier
        score = len(inter) / len(union) * 100 if union else 0
        if m_apprenti <= m_dossier:
            score = max(score, 90)
        if score > meilleur_score:
            meilleur_score = score
            meilleur = apprenti
    return meilleur if meilleur_score >= 60 else None


# ── Drive API ──────────────────────────────────────────────────────────

def connecter_drive():
    if not os.path.exists(CREDENTIALS_PATH):
        print(f"\n❌ ERREUR : fichier credentials.json introuvable !")
        print(f"   Chemin attendu : {CREDENTIALS_PATH}")
        sys.exit(1)

    creds = service_account.Credentials.from_service_account_file(
        CREDENTIALS_PATH, scopes=SCOPES
    )
    service = build("drive", "v3", credentials=creds)
    print("✅ Connecté à Google Drive")
    return service


def lister_dossiers(service, parent_id):
    """Liste les sous-dossiers d'un dossier."""
    q = (f"'{parent_id}' in parents "
         f"and mimeType = 'application/vnd.google-apps.folder' "
         f"and trashed = false")
    all_items = []
    page_token = None
    while True:
        params = {
            "q": q, "pageSize": 1000,
            "fields": "nextPageToken, files(id, name, webViewLink)",
            "supportsAllDrives": True,
            "includeItemsFromAllDrives": True,
        }
        if page_token:
            params["pageToken"] = page_token
        res = service.files().list(**params).execute()
        all_items.extend(res.get("files", []))
        page_token = res.get("nextPageToken")
        if not page_token:
            break
    return all_items


def lister_fichiers(service, parent_id):
    """Liste les fichiers (non-dossiers) d'un dossier."""
    q = (f"'{parent_id}' in parents "
         f"and mimeType != 'application/vnd.google-apps.folder' "
         f"and trashed = false")
    all_items = []
    page_token = None
    while True:
        params = {
            "q": q, "pageSize": 1000,
            "fields": "nextPageToken, files(id, name, mimeType, webViewLink)",
            "supportsAllDrives": True,
            "includeItemsFromAllDrives": True,
        }
        if page_token:
            params["pageToken"] = page_token
        res = service.files().list(**params).execute()
        all_items.extend(res.get("files", []))
        page_token = res.get("nextPageToken")
        if not page_token:
            break
    return all_items


def lister_fichiers_recursif(service, parent_id, profondeur=3):
    """Liste récursivement tous les fichiers."""
    if profondeur <= 0:
        return []
    fichiers = lister_fichiers(service, parent_id)
    for sd in lister_dossiers(service, parent_id):
        fichiers.extend(lister_fichiers_recursif(service, sd["id"], profondeur - 1))
    return fichiers


def chercher_par_nom(service, nom_apprenti):
    """Cherche tous les fichiers contenant le nom de l'apprenti."""
    mots_r = [m for m in nom_apprenti.split() if len(m) > 1][:2]
    if not mots_r:
        return []
    parts = [f"name contains '{m}'" for m in mots_r]
    conditions = " and ".join(parts)

    tous = []
    noms_vus = set()

    # Chercher les dossiers par nom et lister leur contenu
    q_dossiers = (f"mimeType = 'application/vnd.google-apps.folder' "
                  f"and {conditions} and trashed = false")
    try:
        res = service.files().list(
            q=q_dossiers, pageSize=100,
            fields="files(id, name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            corpora="allDrives",
        ).execute()
        for d in res.get("files", []):
            for f in lister_fichiers_recursif(service, d["id"], 2):
                if f["name"] not in noms_vus:
                    noms_vus.add(f["name"])
                    tous.append(f)
    except HttpError:
        pass

    # Chercher les fichiers directement nommés
    q_fichiers = (f"mimeType != 'application/vnd.google-apps.folder' "
                  f"and {conditions} and trashed = false")
    try:
        res = service.files().list(
            q=q_fichiers, pageSize=100,
            fields="files(id, name, mimeType, webViewLink)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            corpora="allDrives",
        ).execute()
        for f in res.get("files", []):
            if f["name"] not in noms_vus:
                noms_vus.add(f["name"])
                tous.append(f)
    except HttpError:
        pass

    return tous


def copier_fichier(service, file_id, parent_id):
    """Copie un fichier Drive vers un dossier cible."""
    body = {"parents": [parent_id]}
    copie = service.files().copy(
        fileId=file_id, body=body,
        fields="id, name, webViewLink",
        supportsAllDrives=True,
    ).execute()
    return copie


def upload_local(service, chemin, nom, parent_id):
    """Upload un fichier local vers un dossier Drive."""
    with open(chemin, "rb") as f:
        contenu = f.read()
    media = MediaIoBaseUpload(io.BytesIO(contenu), mimetype="application/octet-stream", resumable=True)
    meta = {"name": nom, "parents": [parent_id]}
    return service.files().create(
        body=meta, media_body=media,
        fields="id, name, webViewLink",
        supportsAllDrives=True,
    ).execute()


# ── Script principal ───────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  COPIE DES PIECES JOINTES VERS GOOGLE DRIVE")
    print("=" * 60)
    print()

    service = connecter_drive()

    # 1. Lister les dossiers candidats dans le Drive CIBLE
    print("\n📂 Chargement des dossiers candidats dans le Drive CIBLE...")
    dossiers_candidats = {}  # nom_apprenti -> {id, name}

    dossiers_racine = lister_dossiers(service, DRIVE_CIBLE_ID)
    for dr in dossiers_racine:
        if dr["name"] in DOSSIERS_APPRENANTS:
            sous = lister_dossiers(service, dr["id"])
            for sd in sous:
                apprenti = matcher_apprenti(sd["name"])
                if apprenti and apprenti not in dossiers_candidats:
                    dossiers_candidats[apprenti] = {
                        "id": sd["id"],
                        "name": sd["name"],
                    }

    print(f"   -> {len(dossiers_candidats)} dossiers candidats trouvés")

    if not dossiers_candidats:
        print("\n❌ Aucun dossier candidat trouvé dans le Drive CIBLE !")
        print("   Vérifiez que le Drive contient des dossiers dans")
        print(f"   'Dossiers apprenants', 'PARTIE 2...', etc.")
        sys.exit(1)

    # 2. Pour chaque candidat, chercher ses fichiers et les copier
    print("\n🔍 Recherche et copie des pièces jointes...\n")

    total_copies = 0
    total_skip = 0
    total_erreurs = 0

    for apprenti, dossier in dossiers_candidats.items():
        # Fichiers déjà dans le dossier cible
        existants = {f["name"] for f in lister_fichiers(service, dossier["id"])}

        # Chercher les fichiers de cet apprenti dans tout le Drive
        fichiers = chercher_par_nom(service, apprenti)

        # Filtrer : garder seulement les fichiers pertinents
        pieces_a_copier = []
        for f in fichiers:
            # Ne pas recopier un fichier déjà présent
            if f["name"] in existants:
                continue
            # Ne pas copier les dossiers Google natifs (Docs, Sheets sans contenu)
            mime = f.get("mimeType", "")
            if mime == "application/vnd.google-apps.folder":
                continue
            pieces_a_copier.append(f)

        if not pieces_a_copier:
            continue

        print(f"  👤 {apprenti} -> dossier '{dossier['name']}'")

        for f in pieces_a_copier:
            try:
                copier_fichier(service, f["id"], dossier["id"])
                print(f"     ✅ {f['name']}")
                total_copies += 1
            except HttpError as e:
                if "exportSizeLimitExceeded" in str(e):
                    total_skip += 1
                else:
                    print(f"     ❌ {f['name']} : {e}")
                    total_erreurs += 1
            except Exception as e:
                print(f"     ❌ {f['name']} : {e}")
                total_erreurs += 1

    # 3. Chercher aussi les fichiers locaux (dossier OPCO sur le Mac)
    local_paths = [
        os.path.expanduser("~/Downloads/DOSSIER OPCO DEJA ENVOYE"),
        os.path.expanduser("~/Desktop/DOSSIER OPCO DEJA ENVOYE"),
    ]
    for local_path in local_paths:
        if os.path.isdir(local_path):
            print(f"\n📁 Scan du dossier local : {local_path}")
            for root, dirs, files in os.walk(local_path):
                for fname in files:
                    if fname.startswith("."):
                        continue
                    chemin = os.path.join(root, fname)
                    # Trouver à quel apprenti ce fichier correspond
                    for apprenti, dossier in dossiers_candidats.items():
                        if nom_dans_fichier(apprenti, fname) or nom_dans_fichier(apprenti, root):
                            existants = {f["name"] for f in lister_fichiers(service, dossier["id"])}
                            if fname not in existants:
                                try:
                                    upload_local(service, chemin, fname, dossier["id"])
                                    print(f"     ✅ (local) {fname} -> {apprenti}")
                                    total_copies += 1
                                except Exception as e:
                                    print(f"     ❌ (local) {fname} : {e}")
                                    total_erreurs += 1
                            break

    # Résumé
    print("\n" + "=" * 60)
    print(f"  TERMINÉ !")
    print(f"  ✅ {total_copies} fichiers copiés")
    print(f"  ⏭️  {total_skip} ignorés (trop volumineux)")
    print(f"  ❌ {total_erreurs} erreurs")
    print("=" * 60)
    print()
    input("Appuyez sur Entrée pour fermer...")


if __name__ == "__main__":
    main()
