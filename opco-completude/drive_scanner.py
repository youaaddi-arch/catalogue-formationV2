"""Module de scan Google Drive pour l'application OPCO EP."""

import io
import logging
import re
from typing import Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload, MediaIoBaseUpload

import config

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive"]

# Patterns de noms de classes connus
CLASSE_PATTERNS = re.compile(
    r'\b(NTC\s*\d+|CC\s*\d+|REM\s*\d+|DP\s*\d*|TP\s+\w+|BTS\s+\w+|'
    r'AIS\s*\d*|DWWM\s*\d*|CDA\s*\d*|TSSR\s*\d*|SIO\s*\d*|BACHELOR\s*\w*)',
    re.IGNORECASE
)


class DriveScanner:
    """Scanner pour les Google Drives OPCO EP."""

    def __init__(self, credentials_path: str = None):
        self.credentials_path = credentials_path or config.CREDENTIALS_PATH
        self.service = None
        self._cache = {}

    def connect(self):
        """Établit la connexion au Google Drive API."""
        try:
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path, scopes=SCOPES
            )
            self.service = build("drive", "v3", credentials=credentials)
            logger.info("Connexion Google Drive établie avec succès")
            return True
        except Exception as e:
            logger.error(f"Erreur de connexion Google Drive: {e}")
            return False

    def _list_files(self, query: str, drive_id: str = None,
                    page_size: int = 1000) -> list:
        """Liste les fichiers selon une requête Drive API.

        Essaie d'abord avec corpora=allDrives, puis sans corpora en fallback.
        """
        cache_key = f"{query}|{drive_id}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        all_files = []
        page_token = None

        try:
            while True:
                params = {
                    "q": query,
                    "pageSize": page_size,
                    "fields": "nextPageToken, files(id, name, mimeType, parents, webViewLink)",
                    "supportsAllDrives": True,
                    "includeItemsFromAllDrives": True,
                    "corpora": "allDrives",
                }
                if page_token:
                    params["pageToken"] = page_token

                results = self.service.files().list(**params).execute()
                files = results.get("files", [])
                all_files.extend(files)

                page_token = results.get("nextPageToken")
                if not page_token:
                    break

            self._cache[cache_key] = all_files
            return all_files

        except HttpError as e:
            logger.error(f"Erreur API Drive: {e}")
            return []

    def _list_folder_contents(self, folder_id: str,
                               folders_only: bool = False) -> list:
        """Liste le contenu d'un dossier spécifique.

        Méthode dédiée pour lister le contenu d'un dossier connu par son ID.
        Essaie plusieurs stratégies car 'in parents' avec corpora=allDrives
        ne fonctionne pas toujours sur les Drives partagés.
        """
        cache_key = f"folder_contents|{folder_id}|{folders_only}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        mime_filter = (
            "mimeType = 'application/vnd.google-apps.folder'"
            if folders_only
            else "mimeType != 'application/vnd.google-apps.folder'"
        )
        q = f"'{folder_id}' in parents and {mime_filter} and trashed = false"

        # Stratégie 1: sans corpora (fonctionne pour les fichiers accessibles)
        try:
            params = {
                "q": q,
                "pageSize": 1000,
                "fields": "nextPageToken, files(id, name, mimeType, parents, webViewLink)",
                "supportsAllDrives": True,
                "includeItemsFromAllDrives": True,
            }
            all_files = []
            page_token = None
            while True:
                if page_token:
                    params["pageToken"] = page_token
                results = self.service.files().list(**params).execute()
                all_files.extend(results.get("files", []))
                page_token = results.get("nextPageToken")
                if not page_token:
                    break
            if all_files:
                self._cache[cache_key] = all_files
                return all_files
        except HttpError as e:
            logger.debug(f"Stratégie 1 échouée pour {folder_id}: {e}")

        # Stratégie 2: avec corpora=allDrives
        try:
            params["corpora"] = "allDrives"
            params.pop("pageToken", None)
            all_files = []
            page_token = None
            while True:
                if page_token:
                    params["pageToken"] = page_token
                results = self.service.files().list(**params).execute()
                all_files.extend(results.get("files", []))
                page_token = results.get("nextPageToken")
                if not page_token:
                    break
            self._cache[cache_key] = all_files
            return all_files
        except HttpError as e:
            logger.debug(f"Stratégie 2 échouée pour {folder_id}: {e}")

        self._cache[cache_key] = []
        return []

    def lister_dossiers_racine(self, drive_id: str) -> list:
        """Liste les dossiers à la racine d'un Drive partagé."""
        return self._list_folder_contents(drive_id, folders_only=True)

    def lister_sous_dossiers(self, parent_id: str, drive_id: str = None) -> list:
        """Liste les sous-dossiers d'un dossier."""
        return self._list_folder_contents(parent_id, folders_only=True)

    def lister_fichiers(self, parent_id: str, drive_id: str = None) -> list:
        """Liste les fichiers (non-dossiers) d'un dossier."""
        return self._list_folder_contents(parent_id, folders_only=False)

    def lister_tout_contenu_recursif(self, parent_id: str,
                                      drive_id: str = None,
                                      profondeur_max: int = 5) -> list:
        """Liste récursivement tous les fichiers dans un dossier et ses sous-dossiers."""
        if profondeur_max <= 0:
            return []

        fichiers = self.lister_fichiers(parent_id)
        sous_dossiers = self.lister_sous_dossiers(parent_id)

        for sd in sous_dossiers:
            fichiers.extend(
                self.lister_tout_contenu_recursif(
                    sd["id"], None, profondeur_max - 1
                )
            )
        return fichiers

    def trouver_dossier_par_nom(self, nom: str, parent_id: str,
                                 drive_id: str = None) -> Optional[dict]:
        """Cherche un dossier par nom exact dans un parent donné."""
        query = (
            f"'{parent_id}' in parents "
            f"and mimeType = 'application/vnd.google-apps.folder' "
            f"and name = '{self._escape_query(nom)}' "
            f"and trashed = false"
        )
        results = self._list_files(query, drive_id)
        return results[0] if results else None

    def trouver_dossiers_apprenants(self, drive_id: str) -> dict:
        """
        Trouve tous les sous-dossiers dans les dossiers d'apprenants du Drive CIBLE.
        Retourne un dict {nom_dossier: {id, name, parent_name, files_count}}.
        """
        dossiers_apprenants = {}
        dossiers_racine = self.lister_dossiers_racine(drive_id)

        for dossier_racine in dossiers_racine:
            if dossier_racine["name"] in config.DOSSIERS_APPRENANTS:
                sous_dossiers = self.lister_sous_dossiers(
                    dossier_racine["id"], drive_id
                )
                for sd in sous_dossiers:
                    dossiers_apprenants[sd["name"]] = {
                        "id": sd["id"],
                        "name": sd["name"],
                        "parent_name": dossier_racine["name"],
                        "webViewLink": sd.get("webViewLink", ""),
                    }

        logger.info(
            f"Trouvé {len(dossiers_apprenants)} dossiers d'apprenants "
            f"dans le Drive CIBLE"
        )
        return dossiers_apprenants

    def trouver_fichiers_transversaux(self, drive_id: str,
                                       nom_dossier: str) -> list:
        """
        Trouve tous les fichiers dans un dossier transversal
        (Factures, APEC, etc.).
        """
        dossiers_racine = self.lister_dossiers_racine(drive_id)

        for dossier in dossiers_racine:
            if dossier["name"].strip().lower() == nom_dossier.strip().lower():
                return self.lister_fichiers(dossier["id"], drive_id)

        # Chercher aussi dans les sous-dossiers si pas trouvé à la racine
        for dossier in dossiers_racine:
            sous_dossiers = self.lister_sous_dossiers(dossier["id"], drive_id)
            for sd in sous_dossiers:
                if sd["name"].strip().lower() == nom_dossier.strip().lower():
                    return self.lister_fichiers(sd["id"], drive_id)

        logger.warning(f"Dossier transversal '{nom_dossier}' non trouvé")
        return []

    def scanner_drive_source(self) -> tuple:
        """
        Scanne le Drive SOURCE (PROMOTIONS PNBS) en cherchant directement
        les dossiers par nom d'apprenti via l'API de recherche Drive.

        Retourne (dossiers_apprenants, fichiers_planning).
        """
        dossiers = {}
        fichiers_planning = []

        try:
            # Recherche directe par nom d'apprenti
            logger.info("Drive SOURCE: recherche directe des dossiers d'apprentis...")
            for nom in config.APPRENTIS:
                mots = [m for m in nom.split() if len(m) > 1]
                if not mots:
                    continue

                mots_recherche = mots[:2]
                query_parts = [
                    f"name contains '{self._escape_query(mot)}'"
                    for mot in mots_recherche
                ]
                query = (
                    f"mimeType = 'application/vnd.google-apps.folder' "
                    f"and {' and '.join(query_parts)} "
                    f"and trashed = false"
                )
                results = self._list_files(query)

                if results:
                    for r in results:
                        dossiers[r["name"]] = {
                            "id": r["id"],
                            "name": r["name"],
                            "parent_name": "Drive SOURCE",
                            "classe_name": "",
                            "webViewLink": r.get("webViewLink", ""),
                        }
                    logger.info(
                        f"  {nom} -> {len(results)} dossier(s): "
                        f"{results[0]['name']}"
                    )

            # Chercher les plannings/calendriers
            logger.info("Drive SOURCE: recherche des plannings...")
            for mot_cle in ["planning", "calendrier"]:
                query = (
                    f"name contains '{mot_cle}' "
                    f"and mimeType != 'application/vnd.google-apps.folder' "
                    f"and trashed = false"
                )
                results = self._list_files(query)
                for f in results:
                    if f["name"] not in {p["name"] for p in fichiers_planning}:
                        fichiers_planning.append(f)

            logger.info(f"Trouvé {len(fichiers_planning)} fichiers planning")

        except Exception as e:
            logger.error(f"Erreur scan Drive SOURCE: {e}", exc_info=True)

        logger.info(
            f"Trouvé {len(dossiers)} dossiers d'apprenants dans le Drive SOURCE"
        )
        return dossiers, fichiers_planning

    def extraire_classe_depuis_planning(self, nom_planning: str) -> str:
        """Extrait le nom de la classe depuis un nom de fichier planning.

        Ex: 'PLANNING CC5.pdf' -> 'CC5'
            'PLANNING NTC 3 2026 à 2027 MONTPELLIER.pdf' -> 'NTC 3'
            'PLANNING 2025 2026 NTC1 MONTPELLIER.pdf' -> 'NTC1'
        """
        match = CLASSE_PATTERNS.search(nom_planning)
        return match.group(1).strip() if match else ""

    def chercher_fichiers_par_nom(self, nom_apprenti: str) -> list:
        """
        Cherche les fichiers d'un apprenti dans le Drive.

        Stratégie combinée:
        1. Chercher les DOSSIERS par nom d'apprenti
        2. Pour chaque dossier trouvé, lister son contenu récursivement
        3. Chercher aussi les FICHIERS directement nommés avec le nom
        """
        mots = [m for m in nom_apprenti.split() if len(m) > 1]
        if not mots:
            return []

        mots_recherche = mots[:2]
        query_parts = [
            f"name contains '{self._escape_query(mot)}'"
            for mot in mots_recherche
        ]
        conditions = " and ".join(query_parts)

        tous_fichiers = []
        noms_vus = set()

        # 1. Chercher les dossiers par nom et lister leur contenu
        query_dossiers = (
            f"mimeType = 'application/vnd.google-apps.folder' "
            f"and {conditions} and trashed = false"
        )
        dossiers = self._list_files(query_dossiers)

        for dossier in dossiers:
            fichiers = self.lister_tout_contenu_recursif(
                dossier["id"], profondeur_max=3
            )
            for f in fichiers:
                if f["name"] not in noms_vus:
                    noms_vus.add(f["name"])
                    tous_fichiers.append(f)

        # 2. Chercher aussi les fichiers nommés directement avec le nom
        query_fichiers = (
            f"mimeType != 'application/vnd.google-apps.folder' "
            f"and {conditions} and trashed = false"
        )
        fichiers_directs = self._list_files(query_fichiers)
        for f in fichiers_directs:
            if f["name"] not in noms_vus:
                noms_vus.add(f["name"])
                tous_fichiers.append(f)

        return tous_fichiers

    def trouver_classe_apprenti(self, nom_apprenti: str) -> str:
        """Trouve la classe d'un apprenti en regardant le dossier parent."""
        mots = [m for m in nom_apprenti.split() if len(m) > 1]
        if not mots:
            return ""

        mots_recherche = mots[:2]
        query_parts = [
            f"name contains '{self._escape_query(mot)}'"
            for mot in mots_recherche
        ]
        query = (
            f"mimeType = 'application/vnd.google-apps.folder' "
            f"and {' and '.join(query_parts)} and trashed = false"
        )
        dossiers = self._list_files(query)

        for d in dossiers:
            parents = d.get("parents", [])
            if not parents:
                continue
            parent_name = self.obtenir_nom_parent(d)
            if not parent_name:
                continue
            # Vérifier si le parent ressemble à un nom de classe
            if CLASSE_PATTERNS.search(parent_name):
                return parent_name

        return ""

    def obtenir_nom_parent(self, file_or_folder: dict) -> str:
        """
        Récupère le nom du dossier parent d'un fichier ou dossier.
        Utilise le champ 'parents' retourné par l'API Drive.
        """
        parents = file_or_folder.get("parents", [])
        if not parents:
            return ""

        parent_id = parents[0]
        cache_key = f"parent_name|{parent_id}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            parent = self.service.files().get(
                fileId=parent_id,
                fields="name",
                supportsAllDrives=True,
            ).execute()
            name = parent.get("name", "")
            self._cache[cache_key] = name
            return name
        except Exception as e:
            logger.error(f"Erreur récupération parent {parent_id}: {e}")
            return ""

    def chercher_fichiers_globaux(self, mot_cle: str) -> list:
        """
        Cherche tous les fichiers contenant un mot-clé dans tout le Drive.
        Utilisé pour les ECF, émargements TCD, plannings, etc.
        """
        mot_escaped = self._escape_query(mot_cle)
        query = (
            f"name contains '{mot_escaped}' "
            f"and mimeType != 'application/vnd.google-apps.folder' "
            f"and trashed = false"
        )
        return self._list_files(query)

    def chercher_dossiers_globaux(self, mot_cle: str) -> list:
        """
        Cherche tous les dossiers contenant un mot-clé dans tout le Drive.
        """
        mot_escaped = self._escape_query(mot_cle)
        query = (
            f"name contains '{mot_escaped}' "
            f"and mimeType = 'application/vnd.google-apps.folder' "
            f"and trashed = false"
        )
        return self._list_files(query)

    def telecharger_fichier(self, file_id: str) -> Optional[bytes]:
        """
        Télécharge un fichier depuis Google Drive par son ID.

        Gère les fichiers Google natifs (Docs, Sheets, Slides) en les
        exportant en PDF, et les fichiers classiques via get_media.

        Returns:
            Le contenu du fichier en bytes, ou None en cas d'erreur.
        """
        if not self.service:
            logger.error("Pas de connexion Drive pour le téléchargement")
            return None

        try:
            # Récupérer les métadonnées pour connaître le mimeType
            meta = self.service.files().get(
                fileId=file_id,
                fields="id, name, mimeType",
                supportsAllDrives=True,
            ).execute()

            mime = meta.get("mimeType", "")
            name = meta.get("name", file_id)

            # Les types Google natifs doivent être exportés
            export_map = {
                "application/vnd.google-apps.document": "application/pdf",
                "application/vnd.google-apps.spreadsheet": "application/pdf",
                "application/vnd.google-apps.presentation": "application/pdf",
                "application/vnd.google-apps.drawing": "application/pdf",
            }

            buf = io.BytesIO()

            if mime in export_map:
                request = self.service.files().export_media(
                    fileId=file_id, mimeType=export_map[mime]
                )
            else:
                request = self.service.files().get_media(
                    fileId=file_id, supportsAllDrives=True
                )

            downloader = MediaIoBaseDownload(buf, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()

            logger.info(f"Téléchargé: {name} ({len(buf.getvalue())} octets)")
            return buf.getvalue()

        except HttpError as e:
            logger.error(f"Erreur téléchargement Drive {file_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Erreur inattendue téléchargement {file_id}: {e}")
            return None

    def creer_dossier(self, nom: str, parent_id: str) -> Optional[dict]:
        """
        Crée un dossier dans Google Drive sous le parent donné.

        Returns:
            Métadonnées du dossier créé {id, name, webViewLink} ou None.
        """
        if not self.service:
            return None

        try:
            metadata = {
                "name": nom,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [parent_id],
            }
            dossier = self.service.files().create(
                body=metadata,
                fields="id, name, webViewLink",
                supportsAllDrives=True,
            ).execute()
            logger.info(f"Dossier créé: {nom} (id={dossier['id']})")
            return dossier
        except HttpError as e:
            logger.error(f"Erreur création dossier '{nom}': {e}")
            return None

    def upload_fichier(self, contenu: bytes, nom_fichier: str,
                       mime_type: str, parent_id: str) -> Optional[dict]:
        """
        Upload un fichier dans un dossier Google Drive.

        Args:
            contenu: Contenu du fichier en bytes
            nom_fichier: Nom du fichier à créer
            mime_type: Type MIME du fichier
            parent_id: ID du dossier parent dans Google Drive

        Returns:
            Métadonnées du fichier créé {id, name, webViewLink} ou None.
        """
        if not self.service:
            return None

        try:
            metadata = {
                "name": nom_fichier,
                "parents": [parent_id],
            }
            media = MediaIoBaseUpload(
                io.BytesIO(contenu),
                mimetype=mime_type,
                resumable=True,
            )
            fichier = self.service.files().create(
                body=metadata,
                media_body=media,
                fields="id, name, webViewLink",
                supportsAllDrives=True,
            ).execute()
            logger.info(
                f"Fichier uploadé: {nom_fichier} -> {parent_id} "
                f"(id={fichier['id']})"
            )
            return fichier
        except HttpError as e:
            logger.error(f"Erreur upload '{nom_fichier}': {e}")
            return None

    def trouver_ou_creer_dossier_apprenti(
        self, nom_apprenti: str, drive_cible_id: str,
        dossier_parent_nom: str = None,
    ) -> Optional[dict]:
        """
        Trouve le dossier Drive d'un apprenti, ou le crée s'il n'existe pas.

        Cherche d'abord dans les sections "Dossiers apprenants" existantes,
        puis crée dans la première section si introuvable.

        Returns:
            {id, name, webViewLink} du dossier trouvé/créé, ou None.
        """
        from matcher import score_correspondance_nom

        dossier_parent_nom = dossier_parent_nom or config.DOSSIERS_APPRENANTS[0]

        # 1. Chercher dans les dossiers existants
        dossiers_racine = self.lister_dossiers_racine(drive_cible_id)
        meilleur_score = 0
        meilleur_match = None

        for dossier_racine in dossiers_racine:
            if dossier_racine["name"] not in config.DOSSIERS_APPRENANTS:
                continue
            sous_dossiers = self.lister_sous_dossiers(
                dossier_racine["id"], drive_cible_id
            )
            for sd in sous_dossiers:
                score = score_correspondance_nom(nom_apprenti, sd["name"])
                if score > meilleur_score:
                    meilleur_score = score
                    meilleur_match = sd

        if meilleur_match and meilleur_score >= config.FUZZY_THRESHOLD:
            logger.info(
                f"Dossier trouvé pour {nom_apprenti}: "
                f"{meilleur_match['name']} (score={meilleur_score:.0f})"
            )
            return meilleur_match

        # 2. Pas trouvé → créer dans le premier dossier "Dossiers apprenants"
        parent_cible = None
        for dr in dossiers_racine:
            if dr["name"] == dossier_parent_nom:
                parent_cible = dr
                break

        if not parent_cible:
            # Créer le dossier parent lui-même
            parent_cible = self.creer_dossier(dossier_parent_nom, drive_cible_id)
            if not parent_cible:
                logger.error(
                    f"Impossible de créer le dossier parent '{dossier_parent_nom}'"
                )
                return None

        nouveau = self.creer_dossier(nom_apprenti, parent_cible["id"])
        return nouveau

    def clear_cache(self):
        """Vide le cache des requêtes."""
        self._cache = {}

    @staticmethod
    def _escape_query(text: str) -> str:
        """Échappe les caractères spéciaux pour les requêtes Drive API."""
        return text.replace("\\", "\\\\").replace("'", "\\'")
