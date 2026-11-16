# 🩺 Medical Triage Multi-Agent System — LangGraph · MCP · FastAPI

![Python](https://img.shields.io/badge/Python-3.10+-blue) ![LangGraph](https://img.shields.io/badge/LangGraph-multi--agent-purple) ![MCP](https://img.shields.io/badge/MCP-FastMCP-orange) ![FastAPI](https://img.shields.io/badge/API-FastAPI-009688) ![Tests](https://img.shields.io/badge/tests-3%20passing-brightgreen)

**EN —** Multi-agent clinical pre-orientation workflow built with **LangGraph** (supervisor pattern), a tool server exposed through the **Model Context Protocol (MCP)**, two **human-in-the-loop** checkpoints (patient + physician), a **FastAPI** backend and a **Streamlit** frontend. Runs fully offline in a deterministic *mock* mode, or with Claude as the LLM.

**Points clés**
- Pattern **Supervisor** + routage conditionnel, état partagé typé (`MedicalState`), checkpointer pour reprendre une session par `thread_id`
- **Human-in-the-Loop** avec `interrupt()` : 5 questions patient dans un même nœud + validation médecin obligatoire avant le rapport
- Outil **MCP** (`check_red_flags`, FastMCP en stdio) appelé par l'agent pour détecter les signes d'alerte
- API REST (5 endpoints), frontend Streamlit (4 écrans), compatible **LangGraph Studio**
- Garde-fous : aucun diagnostic définitif, mention légale vérifiée par le code, tests de scénarios (`pytest`)

**Auteur :** Ali Elfanity — élève ingénieur IA & Data, EMSI Casablanca · [LinkedIn](https://www.linkedin.com/in/ali-elfanity)

---

## Présentation

Projet academique : workflow d'orientation clinique preliminaire base sur
LangGraph, expose via FastAPI, enrichi avec une integration MCP, et
connecte a un frontend Streamlit.

> **Avertissement** : ce projet est un exercice academique. Le systeme
> ne constitue pas un dispositif medical et ne fournit aucun diagnostic
> definitif. Le rapport final mentionne toujours : *"Ce systeme ne
> remplace pas une consultation medicale."*

## 1. Architecture

```
project/
├── backend/
│   ├── app/
│   │   ├── graph.py            # Construction du graphe LangGraph
│   │   ├── state.py            # MedicalState (etat partage)
│   │   ├── llm.py              # Wrapper LLM (Claude reel ou mode mock hors-ligne)
│   │   ├── nodes/
│   │   │   ├── supervisor.py
│   │   │   ├── diagnostic_agent.py
│   │   │   ├── physician_review.py
│   │   │   └── report_agent.py
│   │   ├── tools/
│   │   │   ├── patient_tools.py    # tool ask_patient (HITL patient)
│   │   │   ├── care_tools.py       # tool recommend_interim_care
│   │   │   └── mcp_client.py       # client MCP (check_red_flags)
│   │   └── api.py              # API FastAPI
│   ├── langgraph.json          # Config LangGraph Studio
│   ├── requirements.txt
│   └── .env.example
├── mcp_server/
│   ├── server.py                # Serveur MCP (FastMCP, transport stdio)
│   └── data/red_flags.json      # Referentiel des signes d'alerte
├── frontend/
│   ├── app.py                   # Frontend Streamlit (4 ecrans, theme bleu)
│   └── requirements.txt
└── README.md
```

## 2. Workflow du graphe

```
START -> Supervisor -> DiagnosticAgent
            (boucle ask_patient x5, tool recommend_interim_care,
             verification MCP check_red_flags)
       -> Supervisor -> PhysicianReview (Human-in-the-Loop)
       -> Supervisor -> ReportAgent
       -> Supervisor -> END
```

Le Supervisor est rappele apres chaque agent et decide de l'etape
suivante via une fonction de routage conditionnelle (`route_from_supervisor`),
en fonction de ce qui est deja present dans le `MedicalState` partage.

Deux interruptions Human-in-the-Loop sont implementees avec
`langgraph.types.interrupt()` :
- 5 interruptions successives dans `diagnostic_agent` (une par question
  patient, pattern "multiples interrupts dans un seul noeud") ;
- 1 interruption dans `physician_review` (revue/traitement du medecin
  traitant), obligatoire avant la generation du rapport final.

## 3. Installation

Prerequis : Python 3.10+.

### 3.1 Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# (optionnel) renseigner ANTHROPIC_API_KEY dans .env pour utiliser un vrai LLM
```

> Sans cle API, le systeme fonctionne en **mode mock** (generation
> deterministe a base de regles) : tout le workflow (questions, MCP,
> Human-in-the-Loop, rapport) reste pleinement fonctionnel et testable
> hors-ligne.

### 3.2 Frontend

```bash
cd frontend
pip install -r requirements.txt
```

## 4. Execution

### 4.1 Lancer l'API FastAPI

```bash
cd backend
uvicorn app.api:app --reload --port 8000
```

L'API est alors disponible sur `http://localhost:8000` (documentation
interactive sur `http://localhost:8000/docs`).

Le serveur MCP (`mcp_server/server.py`) n'a pas besoin d'etre lance
manuellement : il est demarre automatiquement comme sous-processus
(transport stdio) par `app/tools/mcp_client.py` lors de l'appel a
l'outil `check_red_flags`.

### 4.2 Lancer le frontend Streamlit

Dans un second terminal :

```bash
cd frontend
export BACKEND_URL=http://localhost:8000   # Windows : set BACKEND_URL=...
streamlit run app.py
```

Ouvrir ensuite `http://localhost:8501`.

### 4.3 Tester le graphe dans LangGraph Studio

```bash
cd backend
langgraph dev
```

Cela ouvre LangGraph Studio sur le graphe `medical_orientation_graph`
(reference dans `langgraph.json`). On peut y visualiser les noeuds,
declencher manuellement les interruptions (patient et medecin) et
observer les etats intermediaires du `MedicalState`.

## 5. Endpoints API

| Methode | Route                                | Description |
|---------|---------------------------------------|--------------|
| POST    | `/sessions/start`                     | Cree un `thread_id` de session |
| POST    | `/consultation/start`                 | Demarre le graphe avec le cas patient initial |
| POST    | `/consultation/resume`                | Reprend le graphe (reponse patient ou medecin) |
| GET     | `/consultation/{thread_id}`           | Etat courant de la consultation |
| GET     | `/consultation/{thread_id}/report`    | Rapport final structure |

## 6. Jeux de tests suggeres (section 13 du cahier des charges)

- **Cas 1 - syndrome respiratoire simple** : toux, leger mal de gorge,
  pas de fievre, pas de difficulte respiratoire -> aucun red flag.
- **Cas 2 - cas avec red flags** : douleur thoracique, difficulte
  respiratoire, fievre elevee -> red flags detectes, recommandation
  intermediaire renforcee.
- **Cas 3 - cas benin** : fatigue legere, pas de symptome marquant ->
  recommandation generale (repos, hydratation, surveillance).

Pour chaque scenario, verifier : les 5 questions sont posees, la
recommandation intermediaire est generee, la revue medecin est
obligatoire, et le rapport final contient bien la mention legale.

## 7. Cadre ethique

- Le systeme est presente exclusivement comme un exercice academique.
- Aucun diagnostic definitif n'est produit : seuls des termes comme
  *orientation clinique preliminaire*, *synthese clinique* et
  *recommandation intermediaire* sont utilises.
- Le rapport final contient toujours la phrase obligatoire : "Ce
  systeme ne remplace pas une consultation medicale." (verifie
  programmatiquement dans `report_agent.py`).

## 8. Document complementaire

Voir `RAPPORT_TECHNIQUE.md` pour le rapport technique court expliquant
l'architecture et les choix realises (livrable demande en section 14).
