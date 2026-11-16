# Rapport technique court

## 1. Objectif et perimetre

Ce projet implemente un workflow multi-agents d'orientation clinique
**preliminaire** avec LangGraph, conformement au cahier des charges
academique fourni. Le systeme guide un cas patient a travers : la
collecte de 5 informations cliniques, une synthese preliminaire, une
revue obligatoire par un medecin traitant (Human-in-the-Loop), puis un
rapport final structure.

## 2. Choix d'architecture

### 2.1 Pattern Supervisor

Le graphe utilise un **Supervisor central** rappele apres chaque agent
metier. Ce choix (plutot qu'un enchainement lineaire fixe) facilite
l'extension future du workflow (ex. ajout d'un agent de triage) sans
modifier la logique des agents existants : il suffit d'enrichir la
fonction de routage `route_from_supervisor`.

### 2.2 Etat partage (`MedicalState`)

Le state est un `TypedDict` unique partage par tous les noeuds,
conformement a l'exemple fourni dans le cahier des charges (section 8),
etendu avec `qa_history`, `red_flags_detected` et `physician_validated`
pour tracer precisement l'avancement de la consultation.

### 2.3 Human-in-the-Loop

Deux mecanismes d'interruption (`langgraph.types.interrupt`) sont
utilises :

1. **Boucle patient** (`diagnostic_agent`) : 5 interruptions
   successives au sein d'un meme noeud. Ce pattern s'appuie sur le
   rejeu deterministe de LangGraph (durable execution) : a chaque
   reprise (`Command(resume=...)`), le noeud est entierement
   reexecute, les interruptions deja resolues renvoient immediatement
   leur valeur en cache, et seule la prochaine question declenche une
   nouvelle pause.
2. **Revue medecin** (`physician_review`) : une interruption unique,
   bloquante, qui empeche la generation du rapport final tant que le
   medecin n'a pas valide une conduite a tenir.

Cette approche permet d'exposer le workflow via une API HTTP sans
etat persistant cote serveur applicatif : tout l'etat (y compris les
interruptions en attente) est conserve par le `checkpointer` LangGraph
(`MemorySaver`), indexe par `thread_id`.

### 2.4 Outils (tools) et MCP

Trois outils sont definis :
- `ask_patient` (LangChain tool + `interrupt`) : pose une question et
  recupere la reponse patient.
- `recommend_interim_care` (LangChain tool) : produit une
  recommandation intermediaire prudente, modulee selon la presence de
  signes d'alerte.
- `check_red_flags` (outil **MCP**, expose par `mcp_server/server.py`
  et appele depuis `tools/mcp_client.py` via un client stdio) : verifie
  la presence de signes d'alerte dans le texte des reponses patient, a
  partir d'un referentiel local (`mcp_server/data/red_flags.json`),
  avec une heuristique simple de gestion de la negation (ex. "aucune
  difficulte respiratoire" n'est pas comptabilise comme un red flag).

Separer cette verification dans un serveur MCP independant illustre
l'integration demandee (section 9) et permettrait, en evolution future,
de remplacer facilement le referentiel local par une source de donnees
externe (base clinique, API tierce) sans modifier le code des agents.

### 2.5 LLM reel vs mode mock

Pour que le projet reste demontrable sans dependance a une cle API
(contrainte d'environnement academique), `app/llm.py` tente d'appeler
un vrai modele Claude (`langchain_anthropic`) si `ANTHROPIC_API_KEY`
est definie, et bascule sinon sur un generateur de texte deterministe
base sur le contenu du state. Les deux modes respectent strictement
les contraintes ethiques (vocabulaire impose, mention legale
obligatoire), verifiees programmatiquement dans `report_agent.py`.

### 2.6 API FastAPI

L'API expose les 5 routes imposees (section 10). Le choix cle est de
ne **pas** dupliquer la logique d'etat cote API : chaque endpoint lit
ou fait progresser directement le graphe LangGraph via
`graph.get_state()` / `graph.invoke()`, l'API se contentant de
serialiser le state et les interruptions en attente (`pending_interrupt`)
pour le frontend.

### 2.7 Frontend Streamlit

Streamlit a ete choisi pour sa rapidite de mise en oeuvre d'une
interface multi-ecrans pilotee par etat, tout en respectant les
contraintes visuelles demandees (palette bleue, typographie soignee
sans emoji) via une feuille de style CSS injectee (polices Sora pour
les titres, Inter pour le texte courant). Les 4 ecrans minimums
(section 11.1) sont implementes comme des fonctions distinctes,
routees via `st.session_state`.

## 3. Limites connues et pistes d'amelioration

- La detection des "red flags" reste une heuristique simple
  (correspondance de mots-cles + detection basique de negation) : un
  systeme reel necessiterait une analyse linguistique plus robuste.
- Le `MemorySaver` est un checkpointer en memoire : en production, on
  utiliserait un checkpointer persistant (ex. SQLite/Postgres) pour
  survivre a un redemarrage du serveur.
- Le mode mock du LLM produit des textes deterministes et non
  generatifs ; il sert uniquement a garantir la testabilite hors-ligne
  du workflow complet.
