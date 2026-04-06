"""Application Flask — Vérification de complétude des dossiers OPCO EP."""

import io
import json
import logging
import os
from datetime import datetime

import pandas as pd
from flask import Flask, jsonify, render_template, request, send_file

import config
from drive_scanner import DriveScanner
from local_scanner import LocalScanner
from excel_reader import lire_excel
from matcher import (
    associer_donnees_excel,
    construire_pieces_apprenti,
    normaliser_nom,
    trouver_dossier_apprenti,
)
from models import Apprenti

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

# État global du scan
scan_state = {
    "apprentis": [],
    "derniere_maj": None,
    "en_cours": False,
    "progression": 0,
    "erreur": None,
    "stats": {},
}


def effectuer_scan():
    """Effectue le scan complet des deux Drives et du fichier Excel."""
    global scan_state

    scan_state["en_cours"] = True
    scan_state["progression"] = 0
    scan_state["erreur"] = None

    try:
        # 1. Connexion au Drive
        logger.info("Connexion au Google Drive...")
        scanner = DriveScanner()
        drive_ok = scanner.connect()
        if not drive_ok:
            logger.warning(
                "Impossible de se connecter au Google Drive. "
                "Le scan continuera avec les fichiers locaux uniquement."
            )

        scan_state["progression"] = 5

        # 2. Scanner le dossier LOCAL d'abord
        logger.info("Scan du dossier local...")
        local_scanner = LocalScanner()
        dossiers_local = local_scanner.scanner_dossiers_apprenants()
        scan_state["progression"] = 10

        # 2b. Lire le fichier Excel (chercher d'abord en local)
        logger.info("Lecture du fichier Excel CONSTATS EP...")
        excel_local = local_scanner.trouver_excel_constats()
        donnees_excel = lire_excel(excel_local or config.EXCEL_PATH)
        scan_state["progression"] = 15

        # 3. Scanner les dossiers d'apprenants dans le Drive CIBLE
        dossiers_cible = {}
        if drive_ok:
            logger.info("Scan des dossiers d'apprenants (Drive CIBLE)...")
            dossiers_cible = scanner.trouver_dossiers_apprenants(config.DRIVE_CIBLE_ID)
        scan_state["progression"] = 25

        # 4. Scanner le Drive SOURCE (promotions → classes → apprentis)
        dossiers_source = {}
        fichiers_planning_classes = []
        if drive_ok:
            logger.info("Scan du Drive SOURCE (PROMOTIONS PNBS)...")
            dossiers_source, fichiers_planning_classes = scanner.scanner_drive_source()
        scan_state["progression"] = 35

        scan_state["progression"] = 40

        # 5. Scanner les dossiers transversaux
        fichiers_factures = []
        fichiers_apec = []
        if drive_ok:
            logger.info("Scan des dossiers transversaux (Drive)...")
            fichiers_factures = scanner.trouver_fichiers_transversaux(
                config.DRIVE_CIBLE_ID, config.DOSSIER_FACTURES
            )
            fichiers_apec = scanner.trouver_fichiers_transversaux(
                config.DRIVE_CIBLE_ID, config.DOSSIER_APEC
            )
        # Ajouter les fichiers transversaux locaux
        from local_scanner import DOSSIER_FACTURES_NOMS, DOSSIER_APEC_NOMS
        fichiers_factures.extend(
            local_scanner.trouver_fichiers_transversaux(DOSSIER_FACTURES_NOMS)
        )
        fichiers_apec.extend(
            local_scanner.trouver_fichiers_transversaux(DOSSIER_APEC_NOMS)
        )
        logger.info(
            f"Fichiers transversaux: {len(fichiers_factures)} factures, "
            f"{len(fichiers_apec)} APEC"
        )
        scan_state["progression"] = 50

        # 6. Pour chaque apprenti, chercher son dossier et vérifier les pièces
        apprentis = []
        total = len(config.APPRENTIS)

        for i, nom_apprenti in enumerate(config.APPRENTIS):
            logger.info(f"Traitement de {nom_apprenti} ({i+1}/{total})...")

            apprenti = Apprenti(
                nom=nom_apprenti,
                nom_normalise=normaliser_nom(nom_apprenti),
            )

            # Chercher le dossier dans Drive CIBLE, Drive SOURCE et LOCAL
            match_cible = trouver_dossier_apprenti(nom_apprenti, dossiers_cible)
            match_source = trouver_dossier_apprenti(nom_apprenti, dossiers_source)
            match_local = trouver_dossier_apprenti(nom_apprenti, dossiers_local)

            # Construire la liste de fichiers en combinant toutes les sources
            fichiers_dossier = []

            # Prendre le meilleur match comme dossier principal
            if match_cible:
                apprenti.dossier_id = match_cible["id"]
                apprenti.dossier_nom = match_cible["nom_match"]
                apprenti.dossier_source = "cible"
            elif match_source:
                apprenti.dossier_id = match_source["id"]
                apprenti.dossier_nom = match_source["nom_match"]
                apprenti.dossier_source = "source"

            # Chercher les fichiers par NOM dans tout le Drive
            # (car le listing par parent ne fonctionne pas)
            if drive_ok:
                fichiers_drive = scanner.chercher_fichiers_par_nom(nom_apprenti)
                fichiers_dossier.extend(fichiers_drive)
                if fichiers_drive:
                    logger.info(
                        f"  -> {len(fichiers_drive)} fichiers Drive"
                    )

            # Ajouter les plannings de classes (ils ne contiennent pas
            # le nom de l'apprenti, donc la recherche par nom ne les trouve pas)
            for pf in fichiers_planning_classes:
                if pf["name"] not in {f["name"] for f in fichiers_dossier}:
                    fichiers_dossier.append(pf)

            if match_local:
                if not match_cible and not match_source:
                    apprenti.dossier_id = match_local["id"]
                    apprenti.dossier_nom = match_local["nom_match"]
                    apprenti.dossier_source = "local"
                fichiers_local = local_scanner.lister_fichiers_recursif(
                    match_local["path"]
                )
                noms_existants = {f["name"] for f in fichiers_dossier}
                for f in fichiers_local:
                    if f["name"] not in noms_existants:
                        fichiers_dossier.append(f)

            # Associer les données Excel
            apprenti.donnees_excel = associer_donnees_excel(
                nom_apprenti, donnees_excel
            )

            # Construire la liste des pièces
            apprenti.pieces = construire_pieces_apprenti(
                apprenti, fichiers_dossier, fichiers_factures, fichiers_apec
            )

            # Calculer le score
            apprenti.calculer_score()

            apprentis.append(apprenti)

            # Mise à jour progression
            scan_state["progression"] = 50 + int((i + 1) / total * 50)

        # 7. Calculer les statistiques globales
        stats = calculer_stats(apprentis)

        scan_state["apprentis"] = apprentis
        scan_state["stats"] = stats
        scan_state["derniere_maj"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        scan_state["progression"] = 100

        logger.info(
            f"Scan terminé: {stats['nb_complets']}/{len(apprentis)} "
            f"dossiers complets"
        )

    except Exception as e:
        logger.error(f"Erreur pendant le scan: {e}", exc_info=True)
        scan_state["erreur"] = str(e)

    finally:
        scan_state["en_cours"] = False


def calculer_stats(apprentis: list) -> dict:
    """Calcule les statistiques globales."""
    nb_total = len(apprentis)
    nb_complets = sum(1 for a in apprentis if a.est_complet)
    nb_incomplets = nb_total - nb_complets

    # Pièces manquantes les plus fréquentes
    manquantes_count = {}
    for a in apprentis:
        for p in a.pieces_manquantes:
            manquantes_count[p.nom] = manquantes_count.get(p.nom, 0) + 1

    top_manquantes = sorted(
        manquantes_count.items(), key=lambda x: x[1], reverse=True
    )[:10]

    # Score moyen
    if apprentis:
        score_moyen = round(
            sum(a.score_completude for a in apprentis) / nb_total, 1
        )
    else:
        score_moyen = 0

    # Dossiers non trouvés
    nb_sans_dossier = sum(1 for a in apprentis if not a.dossier_id)

    return {
        "nb_total": nb_total,
        "nb_complets": nb_complets,
        "nb_incomplets": nb_incomplets,
        "nb_sans_dossier": nb_sans_dossier,
        "score_moyen": score_moyen,
        "top_manquantes": top_manquantes,
        "progression_globale": round(
            (nb_complets / nb_total * 100) if nb_total > 0 else 0, 1
        ),
    }


# --- Routes Flask ---

@app.route("/")
def dashboard():
    """Page principale — Tableau de bord."""
    return render_template(
        "dashboard.html",
        apprentis=scan_state["apprentis"],
        stats=scan_state["stats"],
        derniere_maj=scan_state["derniere_maj"],
        en_cours=scan_state["en_cours"],
        erreur=scan_state["erreur"],
    )


@app.route("/apprenti/<int:index>")
def detail_apprenti(index):
    """Vue détaillée d'un apprenti."""
    if index < 0 or index >= len(scan_state["apprentis"]):
        return "Apprenti non trouvé", 404

    apprenti = scan_state["apprentis"][index]
    return render_template("detail.html", apprenti=apprenti, index=index)


@app.route("/scan", methods=["POST"])
def lancer_scan():
    """Lance un nouveau scan (synchrone pour simplifier)."""
    if scan_state["en_cours"]:
        return jsonify({"status": "already_running"}), 409

    effectuer_scan()
    return jsonify({"status": "completed", "redirect": "/"})


@app.route("/scan/status")
def scan_status():
    """Retourne l'état actuel du scan."""
    return jsonify({
        "en_cours": scan_state["en_cours"],
        "progression": scan_state["progression"],
        "erreur": scan_state["erreur"],
        "derniere_maj": scan_state["derniere_maj"],
    })


@app.route("/export")
def export_excel():
    """Exporte le tableau de complétude en Excel."""
    if not scan_state["apprentis"]:
        return "Aucune donnée à exporter. Lancez un scan d'abord.", 400

    # Construire le DataFrame
    rows = [a.to_dict() for a in scan_state["apprentis"]]
    df = pd.DataFrame(rows)

    # Écrire dans un buffer
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Complétude OPCO EP")

        # Ajuster la largeur des colonnes
        worksheet = writer.sheets["Complétude OPCO EP"]
        for col_idx, col in enumerate(df.columns, 1):
            max_len = max(
                df[col].astype(str).str.len().max(),
                len(col)
            )
            worksheet.column_dimensions[
                worksheet.cell(row=1, column=col_idx).column_letter
            ].width = min(max_len + 2, 50)

    output.seek(0)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=f"completude_opco_ep_{timestamp}.xlsx",
    )


@app.route("/api/apprentis")
def api_apprentis():
    """API JSON — Liste des apprentis avec filtres."""
    filtre_statut = request.args.get("statut")  # complet, incomplet
    filtre_piece = request.args.get("piece_manquante")
    recherche = request.args.get("q", "").lower()

    apprentis = scan_state["apprentis"]

    # Filtrer
    if filtre_statut == "complet":
        apprentis = [a for a in apprentis if a.est_complet]
    elif filtre_statut == "incomplet":
        apprentis = [a for a in apprentis if not a.est_complet]

    if filtre_piece:
        apprentis = [
            a for a in apprentis
            if any(p.id == filtre_piece and p.statut == "manquante"
                   for p in a.pieces)
        ]

    if recherche:
        apprentis = [
            a for a in apprentis
            if recherche in a.nom.lower()
            or recherche in normaliser_nom(a.nom)
        ]

    result = []
    for i, a in enumerate(scan_state["apprentis"]):
        if a in apprentis:
            result.append({
                "index": i,
                "nom": a.nom,
                "score": a.score_completude,
                "nb_trouvees": a.nb_pieces_trouvees,
                "nb_attendues": a.nb_pieces_attendues,
                "dossier": a.dossier_nom,
                "complet": a.est_complet,
                "numero_dossier": (
                    a.donnees_excel.numero_dossier
                    if a.donnees_excel else None
                ),
                "statut_dossier": (
                    a.donnees_excel.statut_dossier
                    if a.donnees_excel else None
                ),
                "pieces": [
                    {
                        "id": p.id,
                        "nom": p.nom,
                        "statut": p.statut,
                        "fichier": p.fichier_nom,
                    }
                    for p in a.pieces
                ],
            })

    return jsonify(result)


@app.route("/settings")
def settings_page():
    """Page de configuration."""
    return render_template(
        "settings.html",
        config={
            "credentials_path": config.CREDENTIALS_PATH,
            "drive_source_id": config.DRIVE_SOURCE_ID,
            "drive_cible_id": config.DRIVE_CIBLE_ID,
            "excel_path": config.EXCEL_PATH,
            "nb_apprentis": len(config.APPRENTIS),
            "nb_pieces": len(config.TOUTES_PIECES),
            "fuzzy_threshold": config.FUZZY_THRESHOLD,
        },
    )


# --- Lancement ---

if __name__ == "__main__":
    logger.info("Démarrage de l'application OPCO EP Complétude...")
    logger.info(f"Credentials: {config.CREDENTIALS_PATH}")
    logger.info(f"Excel: {config.EXCEL_PATH}")
    app.run(debug=config.DEBUG, host="0.0.0.0", port=8080)
