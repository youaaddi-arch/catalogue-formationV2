"""Module de scan Google Drive pour l'application OPCO EP."""

import logging
from typing import Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import config

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


class DriveScanner:
    """Scanner pour les Google Drives OPCO EP."""

    def __init__(self, credentials_path: str = None):
        self.credentials_path = credentials_path or config.CREDENTIALS_PATH
        self.service = None
        self._cache = {}  # Cache des résultats de requêtes

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
        """Liste les fichiers selon une requête Drive API."""
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
                }
                if drive_id:
                    params["driveId"] = drive_id
                    params["corpora"] = "drive"
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

    def lister_dossiers_racine(self, drive_id: str) -> list:
        """Liste les dossiers à la racine d'un Drive partagé."""
        query = (
            f"'{drive_id}' in parents "
            f"and mimeType = 'application/vnd.google-apps.folder' "
            f"and trashed = false"
        )
        return self._list_files(query, drive_id)

    def lister_sous_dossiers(self, parent_id: str, drive_id: str = None) -> list:
        """Liste les sous-dossiers d'un dossier."""
        query = (
            f"'{parent_id}' in parents "
            f"and mimeType = 'application/vnd.google-apps.folder' "
            f"and trashed = false"
        )
        return self._list_files(query, drive_id)

    def lister_fichiers(self, parent_id: str, drive_id: str = None) -> list:
        """Liste les fichiers (non-dossiers) d'un dossier."""
        query = (
            f"'{parent_id}' in parents "
            f"and mimeType != 'application/vnd.google-apps.folder' "
            f"and trashed = false"
        )
        return self._list_files(query, drive_id)

    def lister_tout_contenu_recursif(self, parent_id: str,
                                      drive_id: str = None,
                                      profondeur_max: int = 5) -> list:
        """Liste récursivement tous les fichiers dans un dossier et ses sous-dossiers."""
        if profondeur_max <= 0:
            return []

        fichiers = self.lister_fichiers(parent_id, drive_id)
        sous_dossiers = self.lister_sous_dossiers(parent_id, drive_id)

        for sd in sous_dossiers:
            fichiers.extend(
                self.lister_tout_contenu_recursif(
                    sd["id"], drive_id, profondeur_max - 1
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
        Scanne le Drive SOURCE (PROMOTIONS PNBS) pour trouver les dossiers
        d'apprenants. Cherche en profondeur : promotions → classes → apprentis.

        Retourne (dossiers_apprenants, fichiers_planning_par_classe).
        - dossiers_apprenants: dict {nom: {id, name, parent_name, classe_name}}
        - fichiers_planning: list de fichiers planning trouvés au niveau classe
        """
        dossiers = {}
        fichiers_planning = []

        try:
            drive_id = config.DRIVE_SOURCE_ID
            # Niveau 1 : dossiers racine du Drive (promotions)
            racine = self.lister_sous_dossiers(drive_id, drive_id)
            logger.info(f"Drive SOURCE: {len(racine)} dossiers racine")

            for promo in racine:
                logger.info(f"  Promotion: {promo['name']}")
                # Niveau 2 : sous-dossiers (classes ou apprentis directs)
                niveau2 = self.lister_sous_dossiers(promo["id"], drive_id)

                for item2 in niveau2:
                    # Vérifier si c'est une classe (contient des sous-dossiers)
                    niveau3 = self.lister_sous_dossiers(item2["id"], drive_id)

                    if niveau3:
                        # C'est une classe → les sous-dossiers sont des apprentis
                        logger.info(
                            f"    Classe: {item2['name']} "
                            f"({len(niveau3)} sous-dossiers)"
                        )

                        # Récupérer les fichiers de la classe (planning, etc.)
                        fichiers_classe = self.lister_fichiers(
                            item2["id"], drive_id
                        )
                        for f in fichiers_classe:
                            f["classe_name"] = item2["name"]
                            if "planning" in f["name"].lower():
                                fichiers_planning.append(f)
                                logger.info(
                                    f"      Planning trouvé: {f['name']}"
                                )

                        # Ajouter les apprentis de cette classe
                        for appr in niveau3:
                            dossiers[appr["name"]] = {
                                "id": appr["id"],
                                "name": appr["name"],
                                "parent_name": promo["name"],
                                "classe_name": item2["name"],
                                "webViewLink": appr.get("webViewLink", ""),
                            }

                        # Aller encore plus profond (niveau 4) au cas où
                        for appr in niveau3:
                            niveau4 = self.lister_sous_dossiers(
                                appr["id"], drive_id
                            )
                            for sub in niveau4:
                                # Sous-dossier d'un apprenti (ex: "admin", "émargements")
                                # On ne les ajoute pas comme apprentis,
                                # ils seront scannés récursivement
                                pass
                    else:
                        # Pas de sous-dossiers → c'est peut-être un apprenti direct
                        dossiers[item2["name"]] = {
                            "id": item2["id"],
                            "name": item2["name"],
                            "parent_name": promo["name"],
                            "classe_name": "",
                            "webViewLink": item2.get("webViewLink", ""),
                        }

        except Exception as e:
            logger.error(f"Erreur scan Drive SOURCE: {e}", exc_info=True)

        logger.info(
            f"Trouvé {len(dossiers)} dossiers d'apprenants dans le Drive SOURCE"
        )
        logger.info(
            f"Trouvé {len(fichiers_planning)} fichiers planning de classes"
        )
        return dossiers, fichiers_planning

    def clear_cache(self):
        """Vide le cache des requêtes."""
        self._cache = {}

    @staticmethod
    def _escape_query(text: str) -> str:
        """Échappe les caractères spéciaux pour les requêtes Drive API."""
        return text.replace("\\", "\\\\").replace("'", "\\'")
