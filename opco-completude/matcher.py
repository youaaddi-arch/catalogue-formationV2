"""Module de fuzzy matching pour noms d'apprentis et identification des pièces."""

import logging
import re
import unicodedata
from typing import Optional

from rapidfuzz import fuzz, process

import config
from models import Apprenti, DonnéesExcel, PieceJustificative

logger = logging.getLogger(__name__)


def normaliser_nom(nom: str) -> str:
    """
    Normalise un nom pour la comparaison :
    - Supprime les accents
    - Met en minuscules
    - Remplace les tirets, underscores, apostrophes par des espaces
    - Supprime les espaces multiples
    """
    # Supprimer les accents
    nom = unicodedata.normalize("NFD", nom)
    nom = "".join(c for c in nom if unicodedata.category(c) != "Mn")
    # Minuscules
    nom = nom.lower()
    # Remplacer tirets, underscores, apostrophes par des espaces
    nom = re.sub(r"[-_'\".,]", " ", nom)
    # Supprimer les espaces multiples
    nom = re.sub(r"\s+", " ", nom).strip()
    return nom


def extraire_mots(nom: str) -> set:
    """Extrait les mots significatifs d'un nom (> 1 caractère)."""
    return {mot for mot in normaliser_nom(nom).split() if len(mot) > 1}


def score_correspondance_nom(nom_cherche: str, nom_dossier: str) -> float:
    """
    Calcule un score de correspondance entre un nom cherché et un nom de dossier.
    Prend en compte :
    - L'ordre inversé (NOM PRENOM vs PRENOM NOM)
    - Les variantes d'accents
    - Les mots manquants
    """
    norm_cherche = normaliser_nom(nom_cherche)
    norm_dossier = normaliser_nom(nom_dossier)

    # Score direct (fuzzy ratio)
    score_direct = fuzz.ratio(norm_cherche, norm_dossier)

    # Score par tokens (insensible à l'ordre)
    score_token = fuzz.token_sort_ratio(norm_cherche, norm_dossier)

    # Score par ensemble de tokens (gère les mots en plus/moins)
    score_token_set = fuzz.token_set_ratio(norm_cherche, norm_dossier)

    # Score par mots communs
    mots_cherche = extraire_mots(nom_cherche)
    mots_dossier = extraire_mots(nom_dossier)
    if mots_cherche and mots_dossier:
        intersection = mots_cherche & mots_dossier
        union = mots_cherche | mots_dossier
        score_mots = (len(intersection) / len(union)) * 100 if union else 0
        # Bonus si tous les mots du nom cherché sont présents
        if mots_cherche <= mots_dossier:
            score_mots = max(score_mots, 90)
    else:
        score_mots = 0

    # Prendre le meilleur score pondéré
    return max(score_direct, score_token, score_token_set, score_mots)


def trouver_dossier_apprenti(
    nom_apprenti: str,
    dossiers_disponibles: dict,
    seuil: float = None,
) -> Optional[dict]:
    """
    Trouve le meilleur dossier correspondant à un apprenti.

    Args:
        nom_apprenti: Nom de l'apprenti à chercher
        dossiers_disponibles: Dict {nom_dossier: info_dossier}
        seuil: Score minimum de correspondance (0-100)

    Returns:
        Info du dossier trouvé ou None
    """
    seuil = seuil or config.FUZZY_THRESHOLD

    if not dossiers_disponibles:
        return None

    meilleur_score = 0
    meilleur_dossier = None

    for nom_dossier, info in dossiers_disponibles.items():
        score = score_correspondance_nom(nom_apprenti, nom_dossier)
        if score > meilleur_score:
            meilleur_score = score
            meilleur_dossier = (nom_dossier, info)

    if meilleur_dossier and meilleur_score >= seuil:
        logger.debug(
            f"Match trouvé: '{nom_apprenti}' -> '{meilleur_dossier[0]}' "
            f"(score: {meilleur_score:.0f})"
        )
        return {
            **meilleur_dossier[1],
            "score_match": meilleur_score,
            "nom_match": meilleur_dossier[0],
        }

    logger.debug(
        f"Pas de match pour '{nom_apprenti}' "
        f"(meilleur score: {meilleur_score:.0f})"
    )
    return None


def identifier_piece(nom_fichier: str, pieces_config: list) -> list:
    """
    Identifie à quelles pièces correspond un fichier.

    Args:
        nom_fichier: Nom du fichier à identifier
        pieces_config: Liste de configs de pièces (avec mots_cles)

    Returns:
        Liste des IDs de pièces correspondantes
    """
    nom_lower = normaliser_nom(nom_fichier)
    pieces_trouvees = []

    for piece in pieces_config:
        for mot_cle in piece.get("mots_cles", []):
            mot_cle_norm = normaliser_nom(mot_cle)
            if mot_cle_norm in nom_lower:
                pieces_trouvees.append(piece["id"])
                break

    return pieces_trouvees


def chercher_nom_dans_fichier(nom_apprenti: str, nom_fichier: str,
                               seuil: float = 60) -> bool:
    """
    Vérifie si le nom d'un apprenti apparaît dans le nom d'un fichier.
    Utilisé pour les pièces transversales (factures, APEC).
    """
    mots_apprenti = extraire_mots(nom_apprenti)
    nom_fichier_norm = normaliser_nom(nom_fichier)

    # Vérifier si au moins 2 mots du nom sont dans le fichier
    # (ou tous si le nom n'a qu'un mot)
    mots_trouves = sum(1 for mot in mots_apprenti if mot in nom_fichier_norm)
    seuil_mots = min(2, len(mots_apprenti))

    if mots_trouves >= seuil_mots:
        return True

    # Fallback: fuzzy matching sur le nom complet
    score = fuzz.partial_ratio(normaliser_nom(nom_apprenti), nom_fichier_norm)
    return score >= seuil


def associer_donnees_excel(
    nom_apprenti: str,
    donnees_excel: dict,
    seuil: float = None,
) -> Optional[DonnéesExcel]:
    """
    Trouve les données Excel correspondant à un apprenti par fuzzy matching.
    """
    seuil = seuil or config.FUZZY_THRESHOLD

    if not donnees_excel:
        return None

    meilleur_score = 0
    meilleur_match = None

    for nom_excel, donnees in donnees_excel.items():
        score = score_correspondance_nom(nom_apprenti, nom_excel)
        if score > meilleur_score:
            meilleur_score = score
            meilleur_match = donnees

    if meilleur_match and meilleur_score >= seuil:
        return meilleur_match

    return None


def construire_pieces_apprenti(
    apprenti: Apprenti,
    fichiers_dossier: list,
    fichiers_factures: list,
    fichiers_apec: list,
) -> list:
    """
    Construit la liste des pièces justificatives pour un apprenti
    en analysant les fichiers trouvés.
    """
    pieces = []
    toutes_pieces = config.PIECES_OBLIGATOIRES + config.PIECES_CONDITIONNELLES

    # Vérifier les pièces obligatoires et conditionnelles
    for piece_config in toutes_pieces:
        piece = PieceJustificative(
            id=piece_config["id"],
            nom=piece_config["nom"],
        )

        # Vérifier si la pièce est conditionnelle et non applicable
        if piece_config.get("conditionnel"):
            condition = piece_config.get("condition")
            if condition == "rupture":
                has_rupture = False
                if apprenti.donnees_excel:
                    rupture_val = (apprenti.donnees_excel.rupture or "").lower()
                    has_rupture = rupture_val in ("oui", "yes", "o", "1", "true")
                if not has_rupture:
                    piece.statut = "non_applicable"
                    pieces.append(piece)
                    continue

        # Chercher dans les fichiers du dossier
        for fichier in fichiers_dossier:
            ids_pieces = identifier_piece(
                fichier["name"], [piece_config]
            )
            if piece_config["id"] in ids_pieces:
                piece.statut = "trouvee"
                piece.fichier_nom = fichier["name"]
                piece.fichier_id = fichier["id"]
                piece.fichier_lien = fichier.get("webViewLink", "")
                piece.source = apprenti.dossier_source
                break

        pieces.append(piece)

    # Vérifier les pièces transversales
    for piece_config in config.PIECES_TRANSVERSALES:
        piece = PieceJustificative(
            id=piece_config["id"],
            nom=piece_config["nom"],
        )

        fichiers_a_chercher = (
            fichiers_factures if piece_config["id"] == "facture"
            else fichiers_apec
        )

        for fichier in fichiers_a_chercher:
            # Pour les factures: chercher le nom de l'apprenti dans le fichier
            if chercher_nom_dans_fichier(apprenti.nom, fichier["name"]):
                # Pour APEC, vérifier aussi le mot-clé "apec"
                if piece_config["id"] == "apec":
                    if "apec" not in fichier["name"].lower():
                        continue
                piece.statut = "trouvee"
                piece.fichier_nom = fichier["name"]
                piece.fichier_id = fichier["id"]
                piece.fichier_lien = fichier.get("webViewLink", "")
                piece.source = "cible"
                break

        pieces.append(piece)

    return pieces
