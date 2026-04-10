# Agent Veille & Réponse aux Appels d'Offres — PNBS

Agent intelligent de veille et de réponse automatisée aux appels d'offres de formation professionnelle, construit avec **N8N** (orchestration) et **LangGraph** (agent IA).

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        N8N Workflow                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │  BOAMP   │  │  PLACE   │  │   TED    │  ← Sources AO    │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                  │
│       └──────────┬───┘─────────────┘                        │
│                  ▼                                           │
│         ┌────────────────┐                                  │
│         │  Normalisation  │                                  │
│         └───────┬────────┘                                  │
│                 ▼                                            │
│         ┌────────────────┐                                  │
│         │   Filtrage     │                                   │
│         └───────┬────────┘                                  │
└─────────────────┼───────────────────────────────────────────┘
                  │ HTTP
                  ▼
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI + LangGraph                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐      │
│  │ Analyse  │→ │ Décision │→ │ Génération Réponse   │      │
│  │ (LLM)   │  │          │  │ - Lettre motivation   │      │
│  │          │  │ Score≥0.6│  │ - Mémoire technique   │      │
│  │          │  │    ?     │  │ - Matrice conformité  │      │
│  └──────────┘  └──────────┘  └──────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
                  │
                  ▼
         ┌────────────────┐
         │  Notification   │  → Email, Dashboard
         └────────────────┘
```

## Sources d'appels d'offres

| Source | Type | Couverture |
|--------|------|-----------|
| **BOAMP** | API OpenDataSoft | Marchés publics français |
| **PLACE** | Flux RSS | Plateforme des achats de l'État |
| **TED** | API v3 | Marchés européens (filtré France) |

## Démarrage rapide

### 1. Configuration

```bash
cd n8n-tender-agent
cp config/.env.example .env
# Éditez .env avec vos clés API
```

### 2. Lancement avec Docker

```bash
docker-compose up -d
```

### 3. Accès aux services

| Service | URL | Description |
|---------|-----|-------------|
| **N8N** | http://localhost:5678 | Interface de workflow |
| **API** | http://localhost:8000 | API FastAPI |
| **Docs API** | http://localhost:8000/docs | Documentation Swagger |

### 4. Import du workflow N8N

1. Ouvrez N8N → http://localhost:5678
2. Menu → Import → Sélectionnez `n8n_workflows/tender_agent_workflow.json`
3. Activez le workflow

## API Endpoints

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/api/health` | Vérification de santé |
| `POST` | `/api/analyze` | Analyser un AO |
| `POST` | `/api/generate-response` | Générer une réponse |
| `POST` | `/api/scrape` | Scraping manuel |
| `GET` | `/api/catalogue` | Catalogue formations |
| `GET` | `/api/results` | Résultats de veille |
| `GET` | `/api/stats` | Statistiques |

### Exemple : Analyser un AO manuellement

```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "tender": {
      "title": "Marché de formation management pour la mairie de Paris",
      "description": "Prestation de formation en management, leadership et gestion d équipe pour 50 cadres",
      "buyer": "Mairie de Paris",
      "deadline": "2026-05-15",
      "amount_estimate": "75000",
      "location": "Paris"
    }
  }'
```

## Fonctionnement de l'agent LangGraph

Le graphe LangGraph traite chaque appel d'offres en 4 étapes :

1. **Analyse** — Le LLM évalue la pertinence de l'AO par rapport au catalogue PNBS (110 formations, 13 domaines)
2. **Décision** — Score ≥ 0.6 → Générer une réponse | Score < 0.6 → Ignorer
3. **Génération** — Production d'un dossier de réponse complet :
   - Lettre de motivation
   - Mémoire technique structuré
   - Proposition de formations adaptées
   - Matrice de conformité
4. **Notification** — Email aux responsables + sauvegarde en base

## Lancement sans Docker

```bash
# Installer les dépendances
pip install -r requirements.txt

# Lancer l'API
python -m api.server
```

## Structure du projet

```
n8n-tender-agent/
├── agent/                  # Agent LangGraph
│   ├── state.py           # État du graphe
│   ├── nodes.py           # Nœuds (analyse, génération, etc.)
│   ├── graph.py           # Graphe principal
│   ├── scraper.py         # Scraping BOAMP/PLACE/TED
│   └── catalogue_loader.py # Catalogue formations PNBS
├── api/
│   └── server.py          # Serveur FastAPI
├── n8n_workflows/
│   └── tender_agent_workflow.json  # Workflow N8N importable
├── config/
│   └── .env.example       # Variables d'environnement
├── data/                   # Base SQLite (auto-créée)
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```
