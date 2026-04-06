"""Module de scan des dossiers locaux pour l'application OPCO EP."""

import logging
import os
import re
from pathlib import Path

import config

logger = logging.getLogger(__name__)


class LocalScanner:
    """Scanner pour les dossiers locaux sur le Mac."""

    def __init__(self, base_path: str = None):
        self.base_path = base_path or config.LOCAL_DOSSIER_PATH

    def scanner_dossiers_apprenants(self) -> dict:
        """
        Scanne le dossier local pour trouver les sous-dossiers d'apprenants.
        Retourne un dict {nom_dossier: {id, name, parent_name, files}}.
        """
        dossiers = {}
        base = Path(self.base_path)

        if not base.exists():
            logger.warning(f"Dossier local non trouvé: {self.base_path}")
            return dossiers

        logger.info(f"Scan du dossier local: {self.base_path}")

        # Scanner les sous-dossiers (chaque sous-dossier = un apprenti ou un lot)
        for item in base.iterdir():
            if item.is_dir():
                # Vérifier si c'est un dossier d'apprenti directement
                # ou un dossier contenant des sous-dossiers d'apprentis
                sous_dossiers = [d for d in item.iterdir() if d.is_dir()]
                fichiers = [f for f in item.iterdir() if f.is_file()]

                if sous_dossiers and len(sous_dossiers) > len(fichiers):
                    # C'est probablement un dossier parent (ex: "PARTIE 1")
                    for sd in sous_dossiers:
                        dossiers[sd.name] = {
                            "id": str(sd),
                            "name": sd.name,
                            "parent_name": item.name,
                            "path": str(sd),
                            "webViewLink": "",
                            "source": "local",
                        }
                    logger.info(
                        f"  Dossier parent '{item.name}': "
                        f"{len(sous_dossiers)} sous-dossiers"
                    )
                else:
                    # C'est un dossier d'apprenti
                    dossiers[item.name] = {
                        "id": str(item),
                        "name": item.name,
                        "parent_name": base.name,
                        "path": str(item),
                        "webViewLink": "",
                        "source": "local",
                    }
            elif item.is_file():
                # Fichier à la racine — on le met dans un dossier "racine"
                pass

        logger.info(f"Trouvé {len(dossiers)} dossiers locaux")
        return dossiers

    def lister_fichiers_recursif(self, dossier_path: str) -> list:
        """
        Liste récursivement tous les fichiers dans un dossier local.
        Retourne une liste au même format que DriveScanner.
        """
        fichiers = []
        base = Path(dossier_path)

        if not base.exists():
            return fichiers

        for item in base.rglob("*"):
            if item.is_file() and not item.name.startswith("."):
                fichiers.append({
                    "id": str(item),
                    "name": item.name,
                    "mimeType": _deviner_mime_type(item.name),
                    "webViewLink": "",
                    "path": str(item),
                    "source": "local",
                })

        return fichiers

    def lister_tous_fichiers_racine(self) -> list:
        """
        Liste tous les fichiers à la racine du dossier
        (fichiers non classés dans un sous-dossier).
        """
        fichiers = []
        base = Path(self.base_path)

        if not base.exists():
            return fichiers

        for item in base.iterdir():
            if item.is_file() and not item.name.startswith("."):
                fichiers.append({
                    "id": str(item),
                    "name": item.name,
                    "mimeType": _deviner_mime_type(item.name),
                    "webViewLink": "",
                    "path": str(item),
                    "source": "local",
                })

        return fichiers


def _deviner_mime_type(nom_fichier: str) -> str:
    """Devine le type MIME d'un fichier à partir de son extension."""
    ext = Path(nom_fichier).suffix.lower()
    types = {
        ".pdf": "application/pdf",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".xls": "application/vnd.ms-excel",
        ".doc": "application/msword",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".csv": "text/csv",
    }
    return types.get(ext, "application/octet-stream")
