"""Configuration pour l'application de vérification OPCO EP."""

import os

# Chemin vers le fichier de credentials Google Service Account
CREDENTIALS_PATH = os.environ.get(
    "GOOGLE_CREDENTIALS_PATH",
    os.path.join(os.path.dirname(__file__), "credentials.json")
)

# IDs des Google Drives
DRIVE_SOURCE_ID = "1-1p6IihluGtZTCRFEFDmjYsZIpCsPS_2"  # PROMOTIONS PNBS
DRIVE_CIBLE_ID = "15WG9vMQikQ6dSF3BfGJim-QR23osVCAv"    # Contrôle OPCO EP

# Noms des dossiers dans le Drive CIBLE
DOSSIERS_APPRENANTS = [
    "Dossiers apprenants",
    "PARTIE 2 DOSSIERS APPRENANTS",
    "PARTIE 3 DOSSIERS APPRENANTS",
    "PARTIE 4 DOSSIERS APPRENANTS",
]

DOSSIER_FACTURES = "Factures bloquées"
DOSSIER_APEC = "Accord PEC des factures bloquées"
DOSSIER_INFOS_GENERALES = "Informations générales en lien avec l'activité de votre CFA"

# Chemin vers le fichier Excel CONSTATS EP (local)
EXCEL_PATH = os.environ.get(
    "EXCEL_PATH",
    os.path.join(os.path.dirname(__file__), "EP & CONTROLE MARS 26.xlsx")
)

# Liste des 94 apprentis
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

# Pièces obligatoires à vérifier
PIECES_OBLIGATOIRES = [
    {
        "id": "cerfa",
        "nom": "CERFA (contrat d'apprentissage)",
        "mots_cles": ["cerfa"],
        "obligatoire": True,
    },
    {
        "id": "convention",
        "nom": "Convention de formation",
        "mots_cles": ["convention", "conven", "cf_"],
        "obligatoire": True,
    },
    {
        "id": "cni",
        "nom": "CNI (pièce d'identité)",
        "mots_cles": ["cni", "carte identité", "carte identite", "visa", "passeport", "titre séjour", "titre sejour"],
        "obligatoire": True,
    },
    {
        "id": "planning",
        "nom": "Planning de formation",
        "mots_cles": ["planning"],
        "obligatoire": True,
    },
    {
        "id": "emargement",
        "nom": "Émargements (feuilles de présence)",
        "mots_cles": ["émargement", "emargement", "présence", "presence"],
        "obligatoire": True,
    },
    {
        "id": "attestation",
        "nom": "Attestation matériel/PC",
        "mots_cles": ["attestation", "matériel", "materiel", "pc"],
        "obligatoire": True,
    },
]

PIECES_CONDITIONNELLES = [
    {
        "id": "rupture",
        "nom": "Formulaire de rupture",
        "mots_cles": ["rupture", "résiliation", "resiliation"],
        "conditionnel": True,
        "condition": "rupture",
    },
    {
        "id": "ecf",
        "nom": "ECF (Évaluation en Cours de Formation)",
        "mots_cles": ["ecf"],
        "conditionnel": True,
        "condition": None,
    },
    {
        "id": "devoirs",
        "nom": "Devoirs / QCM / Contrôles",
        "mots_cles": ["devoir", "qcm", "contrôle", "controle", "sujet"],
        "conditionnel": True,
        "condition": None,
    },
]

PIECES_TRANSVERSALES = [
    {
        "id": "facture",
        "nom": "Facture bloquée",
        "dossier": DOSSIER_FACTURES,
        "mots_cles": [],  # Recherche par nom d'apprenti
    },
    {
        "id": "apec",
        "nom": "Accord PEC (APEC)",
        "dossier": DOSSIER_APEC,
        "mots_cles": ["apec"],  # + nom de l'apprenti
    },
]

# Toutes les pièces combinées
TOUTES_PIECES = PIECES_OBLIGATOIRES + PIECES_CONDITIONNELLES + PIECES_TRANSVERSALES

# Dossier local contenant les documents déjà envoyés
LOCAL_DOSSIER_PATH = os.environ.get(
    "LOCAL_DOSSIER_PATH",
    os.path.expanduser("~/Downloads/DOSSIER OPCO DEJA ENVOYE")
)

# Seuil de fuzzy matching (0-100)
FUZZY_THRESHOLD = 70

# Flask config
SECRET_KEY = os.environ.get("SECRET_KEY", "opco-ep-verification-2026")
DEBUG = os.environ.get("FLASK_DEBUG", "True").lower() == "true"
