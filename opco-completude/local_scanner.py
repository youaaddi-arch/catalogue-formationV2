"""Module de scan des dossiers locaux pour l'application OPCO EP."""

import glob
import logging
import os
from pathlib import Path

import config

logger = logging.getLogger(__name__)

# Noms des dossiers contenant les apprentis
DOSSIERS_APPRENANTS_NOMS = [
    "dossiers apprenants",
    "partie 2 dossiers apprenants",
    "partie 3 dossiers apprenants",
    "partie 4 dossiers apprenants",
]

DOSSIER_FACTURES_NOMS = ["factures bloquées", "factures bloquees", "factures bloqu"]
DOSSIER_APEC_NOMS = ["accord pec des factures bloquées", "accord pec des factures bloquees", "accord pec"]


class LocalScanner:
    """Scanner pour les dossiers locaux sur le Mac."""

    def __init__(self, base_path: str = None):
        self.base_path = base_path or config.LOCAL_DOSSIER_PATH
        # Essayer de trouver le dossier par glob si le chemin exact ne marche pas
        if not Path(self.base_path).exists():
            patterns = [
                os.path.expanduser("~/Downloads/DOSSIER*OPCO*ENVOYE*"),
                os.path.expanduser("~/Downloads/DOSSIER*OPCO*"),
            ]
            for pattern in patterns:
                matches = glob.glob(pattern)
                if matches:
                    self.base_path = matches[0]
                    logger.info(f"Dossier local trouvé par glob: {self.base_path}")
                    break

        # Chercher le sous-dossier principal (ex: "PNBS x Opco EP octobre 2025")
        self.racine = self._trouver_racine()
        logger.info(f"Racine locale: {self.racine}")

    def _trouver_racine(self) -> Path:
        """Trouve le dossier racine contenant les dossiers d'apprenants."""
        base = Path(self.base_path)
        if not base.exists():
            return base

        # Vérifier si la base contient directement des dossiers d'apprenants
        for item in base.iterdir():
            if item.is_dir() and item.name.lower() in DOSSIERS_APPRENANTS_NOMS:
                return base

        # Sinon chercher dans les sous-dossiers (ex: "PNBS x Opco EP octobre 2025")
        for item in base.iterdir():
            if item.is_dir():
                for sub in item.iterdir():
                    if sub.is_dir() and sub.name.lower() in DOSSIERS_APPRENANTS_NOMS:
                        return item

        # Fallback: retourner la base
        return base

    def scanner_dossiers_apprenants(self) -> dict:
        """
        Scanne le dossier local pour trouver les sous-dossiers d'apprenants.
        Retourne un dict {nom_dossier: {id, name, parent_name, path}}.
        """
        dossiers = {}

        if not self.racine.exists():
            logger.warning(f"Dossier local non trouvé: {self.racine}")
            return dossiers

        logger.info(f"Scan du dossier local: {self.racine}")

        # Chercher dans les dossiers d'apprenants (Partie 1, 2, 3, 4)
        for item in self.racine.iterdir():
            if not item.is_dir():
                continue
            item_lower = item.name.lower().strip()
            # Matcher les dossiers d'apprenants par mots-clés
            is_dossier_apprenant = (
                item_lower in DOSSIERS_APPRENANTS_NOMS
                or "dossiers apprenants" in item_lower
                or "dossier apprenant" in item_lower
                or (item_lower.startswith("partie") and "apprenants" in item_lower)
            )
            if is_dossier_apprenant:
                logger.info(f"  Scan de '{item.name}'...")
                count = 0
                for apprenti_dir in item.iterdir():
                    if apprenti_dir.is_dir():
                        dossiers[apprenti_dir.name] = {
                            "id": str(apprenti_dir),
                            "name": apprenti_dir.name,
                            "parent_name": item.name,
                            "path": str(apprenti_dir),
                            "webViewLink": "",
                            "source": "local",
                        }
                        count += 1
                logger.info(f"  -> {count} dossiers d'apprenants")

        logger.info(f"Total: {len(dossiers)} dossiers d'apprenants locaux")
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

    def trouver_fichiers_transversaux(self, noms_dossier: list) -> list:
        """
        Trouve tous les fichiers dans un dossier transversal local
        (Factures bloquées, Accord PEC, etc.).
        """
        fichiers = []

        if not self.racine.exists():
            return fichiers

        for item in self.racine.iterdir():
            if item.is_dir() and any(n in item.name.lower() for n in noms_dossier):
                for f in item.rglob("*"):
                    if f.is_file() and not f.name.startswith("."):
                        fichiers.append({
                            "id": str(f),
                            "name": f.name,
                            "mimeType": _deviner_mime_type(f.name),
                            "webViewLink": "",
                            "path": str(f),
                            "source": "local",
                        })
                logger.info(
                    f"  Dossier transversal '{item.name}': {len(fichiers)} fichiers"
                )

        return fichiers

    def trouver_excel_constats(self) -> str | None:
        """Cherche le fichier Excel CONSTATS EP dans le dossier local."""
        if not self.racine.exists():
            return None

        for item in self.racine.iterdir():
            if item.is_file() and "controle" in item.name.lower() and item.suffix.lower() in (".xlsx", ".xls"):
                logger.info(f"  Fichier Excel trouvé: {item}")
                return str(item)

        for item in self.racine.iterdir():
            if item.is_file() and "constats" in item.name.lower() and item.suffix.lower() in (".xlsx", ".xls"):
                logger.info(f"  Fichier Excel trouvé: {item}")
                return str(item)

        return None


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
