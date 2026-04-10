"""
Chargement et parsing du catalogue de formations PNBS depuis le fichier HTML.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from bs4 import BeautifulSoup


# Catalogue intégré extrait du HTML — les formations PNBS 2025
CATALOGUE_FORMATIONS = [
    # === Management & Encadrement ===
    {"id": "MGT-001", "domain": "Management & Encadrement", "title": "Manager une équipe au quotidien", "duration": "3 jours", "price": 1890, "cpf": True, "certification": "RS6240", "target": "Managers, chefs d'équipe", "demand": "Forte"},
    {"id": "MGT-002", "domain": "Management & Encadrement", "title": "Leadership et management stratégique", "duration": "5 jours", "price": 3200, "cpf": True, "certification": "RNCP36513", "target": "Dirigeants, cadres supérieurs", "demand": "Forte"},
    {"id": "MGT-003", "domain": "Management & Encadrement", "title": "Gestion des conflits en entreprise", "duration": "2 jours", "price": 1290, "cpf": False, "certification": None, "target": "Managers, RH", "demand": "Élevée"},
    {"id": "MGT-004", "domain": "Management & Encadrement", "title": "Conduite du changement", "duration": "3 jours", "price": 1890, "cpf": True, "certification": "RS6056", "target": "Managers, chefs de projet", "demand": "En hausse"},
    {"id": "MGT-005", "domain": "Management & Encadrement", "title": "Management à distance et hybride", "duration": "2 jours", "price": 1290, "cpf": False, "certification": None, "target": "Managers", "demand": "Forte"},
    {"id": "MGT-006", "domain": "Management & Encadrement", "title": "Techniques de délégation efficace", "duration": "1 jour", "price": 690, "cpf": False, "certification": None, "target": "Managers", "demand": "Stable"},
    {"id": "MGT-007", "domain": "Management & Encadrement", "title": "Animation de réunions productives", "duration": "1 jour", "price": 690, "cpf": False, "certification": None, "target": "Tout manager", "demand": "Stable"},
    {"id": "MGT-008", "domain": "Management & Encadrement", "title": "Prise de poste managériale", "duration": "3 jours", "price": 1890, "cpf": True, "certification": "RS6240", "target": "Nouveaux managers", "demand": "Forte"},
    {"id": "MGT-009", "domain": "Management & Encadrement", "title": "Management intergénérationnel", "duration": "2 jours", "price": 1290, "cpf": False, "certification": None, "target": "Managers", "demand": "En hausse"},

    # === Commerce & Relation Client ===
    {"id": "COM-001", "domain": "Commerce & Relation Client", "title": "Techniques de vente et négociation", "duration": "3 jours", "price": 1890, "cpf": True, "certification": "RS5840", "target": "Commerciaux", "demand": "Forte"},
    {"id": "COM-002", "domain": "Commerce & Relation Client", "title": "Prospection commerciale B2B", "duration": "2 jours", "price": 1290, "cpf": False, "certification": None, "target": "Commerciaux, business developers", "demand": "Élevée"},
    {"id": "COM-003", "domain": "Commerce & Relation Client", "title": "Relation client et fidélisation", "duration": "2 jours", "price": 1290, "cpf": True, "certification": "RS6012", "target": "Service client, commerciaux", "demand": "Forte"},
    {"id": "COM-004", "domain": "Commerce & Relation Client", "title": "Social selling et LinkedIn", "duration": "1 jour", "price": 790, "cpf": False, "certification": None, "target": "Commerciaux, marketing", "demand": "En hausse"},
    {"id": "COM-005", "domain": "Commerce & Relation Client", "title": "Gestion des réclamations clients", "duration": "1 jour", "price": 690, "cpf": False, "certification": None, "target": "Service client", "demand": "Stable"},
    {"id": "COM-006", "domain": "Commerce & Relation Client", "title": "E-commerce et vente en ligne", "duration": "3 jours", "price": 1890, "cpf": True, "certification": "RS6290", "target": "Responsables e-commerce", "demand": "Forte"},
    {"id": "COM-007", "domain": "Commerce & Relation Client", "title": "Marketing digital et réseaux sociaux", "duration": "3 jours", "price": 1890, "cpf": True, "certification": "RS6166", "target": "Marketing, communication", "demand": "Forte"},
    {"id": "COM-008", "domain": "Commerce & Relation Client", "title": "CRM et gestion de la relation client", "duration": "2 jours", "price": 1290, "cpf": False, "certification": None, "target": "Commerciaux, marketing", "demand": "En hausse"},

    # === Ressources Humaines ===
    {"id": "RH-001", "domain": "Ressources Humaines", "title": "Gestion administrative du personnel", "duration": "3 jours", "price": 1690, "cpf": True, "certification": "RNCP34560", "target": "Assistants RH, gestionnaires de paie", "demand": "Stable"},
    {"id": "RH-002", "domain": "Ressources Humaines", "title": "Droit du travail pour managers", "duration": "2 jours", "price": 1290, "cpf": False, "certification": None, "target": "Managers, RH", "demand": "Élevée"},
    {"id": "RH-003", "domain": "Ressources Humaines", "title": "Conduite d'entretiens professionnels", "duration": "2 jours", "price": 1290, "cpf": True, "certification": "RS5990", "target": "Managers, RH", "demand": "Forte"},
    {"id": "RH-004", "domain": "Ressources Humaines", "title": "Recrutement et intégration", "duration": "3 jours", "price": 1890, "cpf": True, "certification": "RS6450", "target": "RH, managers recruteurs", "demand": "Forte"},
    {"id": "RH-005", "domain": "Ressources Humaines", "title": "GPEC et gestion des talents", "duration": "2 jours", "price": 1490, "cpf": False, "certification": None, "target": "DRH, responsables RH", "demand": "En hausse"},
    {"id": "RH-006", "domain": "Ressources Humaines", "title": "Prévention des risques psychosociaux", "duration": "2 jours", "price": 1290, "cpf": False, "certification": None, "target": "RH, managers, CSE", "demand": "Forte"},
    {"id": "RH-007", "domain": "Ressources Humaines", "title": "Formation de formateurs", "duration": "3 jours", "price": 1890, "cpf": True, "certification": "RS6413", "target": "Formateurs internes, RH", "demand": "Élevée"},

    # === Bureautique & Digital ===
    {"id": "BUR-001", "domain": "Bureautique & Digital", "title": "Excel avancé - Tableaux croisés et macros", "duration": "2 jours", "price": 990, "cpf": True, "certification": "RS6289 (TOSA)", "target": "Tout collaborateur", "demand": "Forte"},
    {"id": "BUR-002", "domain": "Bureautique & Digital", "title": "Word et PowerPoint professionnel", "duration": "2 jours", "price": 890, "cpf": True, "certification": "RS6289 (TOSA)", "target": "Tout collaborateur", "demand": "Stable"},
    {"id": "BUR-003", "domain": "Bureautique & Digital", "title": "Microsoft 365 - Outils collaboratifs", "duration": "2 jours", "price": 990, "cpf": False, "certification": None, "target": "Tout collaborateur", "demand": "En hausse"},
    {"id": "BUR-004", "domain": "Bureautique & Digital", "title": "Power BI - Analyse de données", "duration": "3 jours", "price": 1690, "cpf": True, "certification": "RS6290", "target": "Analystes, managers", "demand": "Forte"},
    {"id": "BUR-005", "domain": "Bureautique & Digital", "title": "Culture digitale et transformation numérique", "duration": "1 jour", "price": 690, "cpf": False, "certification": None, "target": "Tout collaborateur", "demand": "En hausse"},

    # === Intelligence Artificielle ===
    {"id": "IA-001", "domain": "Intelligence Artificielle", "title": "IA générative pour les professionnels", "duration": "2 jours", "price": 1490, "cpf": False, "certification": None, "target": "Tout professionnel", "demand": "Forte"},
    {"id": "IA-002", "domain": "Intelligence Artificielle", "title": "ChatGPT et outils IA au quotidien", "duration": "1 jour", "price": 790, "cpf": False, "certification": None, "target": "Tout collaborateur", "demand": "Forte"},
    {"id": "IA-003", "domain": "Intelligence Artificielle", "title": "IA pour les RH et le recrutement", "duration": "1 jour", "price": 890, "cpf": False, "certification": None, "target": "RH, recruteurs", "demand": "En hausse"},
    {"id": "IA-004", "domain": "Intelligence Artificielle", "title": "Data Science et Machine Learning", "duration": "5 jours", "price": 3490, "cpf": True, "certification": "RS6821", "target": "Développeurs, analystes", "demand": "Forte"},
    {"id": "IA-005", "domain": "Intelligence Artificielle", "title": "Automatisation des processus par l'IA", "duration": "2 jours", "price": 1490, "cpf": False, "certification": None, "target": "Managers, DSI", "demand": "En hausse"},

    # === Cybersécurité ===
    {"id": "CYB-001", "domain": "Cybersécurité", "title": "Sensibilisation à la cybersécurité", "duration": "1 jour", "price": 790, "cpf": False, "certification": None, "target": "Tout collaborateur", "demand": "Forte"},
    {"id": "CYB-002", "domain": "Cybersécurité", "title": "Sécurité des systèmes d'information", "duration": "3 jours", "price": 2290, "cpf": True, "certification": "RS6680", "target": "DSI, administrateurs", "demand": "Forte"},
    {"id": "CYB-003", "domain": "Cybersécurité", "title": "RGPD et protection des données", "duration": "2 jours", "price": 1290, "cpf": True, "certification": "RS5810", "target": "DPO, juristes, RH", "demand": "Élevée"},
    {"id": "CYB-004", "domain": "Cybersécurité", "title": "Gestion des incidents de sécurité", "duration": "2 jours", "price": 1690, "cpf": False, "certification": None, "target": "DSI, RSSI", "demand": "En hausse"},

    # === Comptabilité & Finance ===
    {"id": "FIN-001", "domain": "Comptabilité & Finance", "title": "Comptabilité générale - Les fondamentaux", "duration": "3 jours", "price": 1690, "cpf": True, "certification": "RNCP34680", "target": "Comptables, assistants", "demand": "Stable"},
    {"id": "FIN-002", "domain": "Comptabilité & Finance", "title": "Analyse financière et tableaux de bord", "duration": "2 jours", "price": 1490, "cpf": True, "certification": "RS6120", "target": "Contrôleurs de gestion", "demand": "Élevée"},
    {"id": "FIN-003", "domain": "Comptabilité & Finance", "title": "Gestion de trésorerie", "duration": "2 jours", "price": 1490, "cpf": False, "certification": None, "target": "DAF, trésoriers", "demand": "Stable"},
    {"id": "FIN-004", "domain": "Comptabilité & Finance", "title": "Fiscalité d'entreprise", "duration": "2 jours", "price": 1290, "cpf": False, "certification": None, "target": "Comptables, DAF", "demand": "Stable"},

    # === Langues ===
    {"id": "LNG-001", "domain": "Langues", "title": "Anglais professionnel - Niveau intermédiaire", "duration": "30h", "price": 1890, "cpf": True, "certification": "RS6151 (TOEIC)", "target": "Tout collaborateur", "demand": "Forte"},
    {"id": "LNG-002", "domain": "Langues", "title": "Anglais des affaires - Niveau avancé", "duration": "30h", "price": 2190, "cpf": True, "certification": "RS6151 (TOEIC)", "target": "Cadres, commerciaux", "demand": "Forte"},
    {"id": "LNG-003", "domain": "Langues", "title": "FLE - Français Langue Étrangère", "duration": "60h", "price": 2490, "cpf": True, "certification": "RS6180 (TCF)", "target": "Collaborateurs non francophones", "demand": "Élevée"},

    # === Sécurité & Prévention ===
    {"id": "SEC-001", "domain": "Sécurité & Prévention", "title": "SST - Sauveteur Secouriste du Travail", "duration": "2 jours", "price": 290, "cpf": True, "certification": "RS6410", "target": "Tout salarié", "demand": "Forte"},
    {"id": "SEC-002", "domain": "Sécurité & Prévention", "title": "Habilitation électrique (BS-BE)", "duration": "2 jours", "price": 590, "cpf": True, "certification": "Certification NFC 18-510", "target": "Personnel non-électricien", "demand": "Forte"},
    {"id": "SEC-003", "domain": "Sécurité & Prévention", "title": "CACES - Chariots élévateurs R489", "duration": "3 jours", "price": 890, "cpf": True, "certification": "CACES R489", "target": "Caristes, magasiniers", "demand": "Forte"},
    {"id": "SEC-004", "domain": "Sécurité & Prévention", "title": "Document Unique et évaluation des risques", "duration": "2 jours", "price": 1290, "cpf": False, "certification": None, "target": "RH, responsables sécurité", "demand": "Élevée"},

    # === BTP & Construction ===
    {"id": "BTP-001", "domain": "BTP & Construction", "title": "Chef de chantier - Perfectionnement", "duration": "5 jours", "price": 2490, "cpf": True, "certification": "RNCP35529", "target": "Chefs de chantier", "demand": "Forte"},
    {"id": "BTP-002", "domain": "BTP & Construction", "title": "Lecture de plans et métrés", "duration": "3 jours", "price": 1490, "cpf": False, "certification": None, "target": "Techniciens, conducteurs de travaux", "demand": "Élevée"},
    {"id": "BTP-003", "domain": "BTP & Construction", "title": "Réglementation thermique RE2020", "duration": "2 jours", "price": 1290, "cpf": False, "certification": None, "target": "Architectes, bureaux d'études", "demand": "Forte"},
    {"id": "BTP-004", "domain": "BTP & Construction", "title": "AutoCAD / Revit BIM", "duration": "5 jours", "price": 2890, "cpf": True, "certification": "RS6200", "target": "Dessinateurs, projeteurs", "demand": "Forte"},

    # === Transport & Logistique ===
    {"id": "LOG-001", "domain": "Transport & Logistique", "title": "Gestion de la chaîne logistique (Supply Chain)", "duration": "3 jours", "price": 1890, "cpf": True, "certification": "RS6520", "target": "Responsables logistique", "demand": "Forte"},
    {"id": "LOG-002", "domain": "Transport & Logistique", "title": "Gestion des stocks et approvisionnements", "duration": "2 jours", "price": 1290, "cpf": False, "certification": None, "target": "Magasiniers, gestionnaires", "demand": "Élevée"},
    {"id": "LOG-003", "domain": "Transport & Logistique", "title": "Réglementation transport de marchandises", "duration": "2 jours", "price": 1090, "cpf": False, "certification": None, "target": "Transporteurs, logisticiens", "demand": "Stable"},
    {"id": "LOG-004", "domain": "Transport & Logistique", "title": "Lean Management et amélioration continue", "duration": "3 jours", "price": 1890, "cpf": True, "certification": "RS6340", "target": "Managers, ingénieurs", "demand": "Forte"},

    # === Hôtellerie, Restauration, Café (HCR) ===
    {"id": "HCR-001", "domain": "Hôtellerie & Restauration", "title": "HACCP - Hygiène alimentaire", "duration": "2 jours", "price": 390, "cpf": True, "certification": "Obligatoire", "target": "Personnel de restauration", "demand": "Forte"},
    {"id": "HCR-002", "domain": "Hôtellerie & Restauration", "title": "Permis d'exploitation (débit de boissons)", "duration": "2.5 jours", "price": 490, "cpf": True, "certification": "Obligatoire", "target": "Gérants, exploitants", "demand": "Forte"},
    {"id": "HCR-003", "domain": "Hôtellerie & Restauration", "title": "Management en hôtellerie-restauration", "duration": "3 jours", "price": 1690, "cpf": False, "certification": None, "target": "Managers HCR", "demand": "Élevée"},
    {"id": "HCR-004", "domain": "Hôtellerie & Restauration", "title": "Accueil et service client en hôtellerie", "duration": "2 jours", "price": 990, "cpf": False, "certification": None, "target": "Personnel d'accueil", "demand": "Stable"},

    # === Développement Personnel ===
    {"id": "DEV-001", "domain": "Développement Personnel", "title": "Prise de parole en public", "duration": "2 jours", "price": 1290, "cpf": False, "certification": None, "target": "Tout professionnel", "demand": "Élevée"},
    {"id": "DEV-002", "domain": "Développement Personnel", "title": "Gestion du temps et des priorités", "duration": "2 jours", "price": 1090, "cpf": False, "certification": None, "target": "Tout professionnel", "demand": "Forte"},
    {"id": "DEV-003", "domain": "Développement Personnel", "title": "Gestion du stress et bien-être au travail", "duration": "2 jours", "price": 1090, "cpf": False, "certification": None, "target": "Tout salarié", "demand": "En hausse"},
    {"id": "DEV-004", "domain": "Développement Personnel", "title": "Communication interpersonnelle", "duration": "2 jours", "price": 1190, "cpf": False, "certification": None, "target": "Tout professionnel", "demand": "Élevée"},
    {"id": "DEV-005", "domain": "Développement Personnel", "title": "Bilan de compétences", "duration": "24h", "price": 1800, "cpf": True, "certification": "Cadre légal", "target": "Tout salarié", "demand": "Forte"},
]


def get_catalogue() -> list[dict]:
    """Retourne le catalogue complet des formations."""
    return CATALOGUE_FORMATIONS


def get_domains() -> list[str]:
    """Retourne la liste des domaines de formation."""
    return list({f["domain"] for f in CATALOGUE_FORMATIONS})


def search_formations(query: str, domain: str | None = None, cpf_only: bool = False) -> list[dict]:
    """Recherche des formations par mots-clés."""
    results = CATALOGUE_FORMATIONS
    if domain:
        results = [f for f in results if f["domain"].lower() == domain.lower()]
    if cpf_only:
        results = [f for f in results if f["cpf"]]
    if query:
        query_lower = query.lower()
        results = [
            f for f in results
            if query_lower in f["title"].lower()
            or query_lower in f["domain"].lower()
            or query_lower in f.get("target", "").lower()
        ]
    return results
