"""
mcp_server/server.py
---------------------
Serveur MCP (Model Context Protocol) exposant des outils utilises par
les agents du backend LangGraph, via le client `backend/app/tools/mcp_client.py`.

Outils exposes :
- check_red_flags(symptoms: str) -> dict
      Verifie la presence de signes d'alerte ("red flags") dans le texte
      des symptomes rapportes, a partir d'un referentiel local (data/red_flags.json).
- get_general_advice(topic: str) -> str
      Retourne un conseil general (non medical) sur un theme donne
      (repos, hydratation, surveillance...).

Lancement direct (mode stdio, utilise automatiquement par mcp_client.py) :
    python mcp_server/server.py
"""

import json
import os
import unicodedata

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("medical-orientation-tools")

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
RED_FLAGS_PATH = os.path.join(DATA_DIR, "red_flags.json")


def _strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(c for c in normalized if not unicodedata.combining(c))


def _load_red_flags():
    with open(RED_FLAGS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)["red_flags"]


_NEGATION_WORDS = ["pas de", "pas d'", "aucun", "aucune", "sans", "non, pas", " non "]


def _is_negated(text: str, keyword: str, window: int = 18) -> bool:
    """Verification heuristique simple : si un mot de negation precede
    immediatement le mot-cle (dans une fenetre de `window` caracteres),
    on considere l'occurrence comme negative (ex: 'aucune difficulte
    respiratoire')."""
    idx = text.find(keyword)
    if idx == -1:
        return False
    start = max(0, idx - window)
    preceding = text[start:idx]
    return any(neg in preceding for neg in _NEGATION_WORDS)


@mcp.tool()
def check_red_flags(symptoms: str) -> dict:
    """
    Analyse un texte de symptomes patient et indique si des signes
    d'alerte (red flags) sont presents, d'apres un referentiel local.

    Args:
        symptoms: texte libre decrivant les symptomes / reponses du patient.

    Returns:
        dict avec les cles `detected` (bool), `matches` (list de dict
        keyword/category/severity) et `note` (str).
    """
    normalized = _strip_accents(symptoms.lower())
    flags = _load_red_flags()

    matches = []
    for flag in flags:
        keyword_norm = _strip_accents(flag["keyword"].lower())
        if keyword_norm in normalized and not _is_negated(normalized, keyword_norm):
            matches.append(flag)

    return {
        "detected": len(matches) > 0,
        "matches": matches,
        "note": (
            "Cette verification est un outil d'aide academique et ne "
            "remplace pas une evaluation medicale professionnelle."
        ),
    }


@mcp.tool()
def get_general_advice(topic: str) -> str:
    """
    Retourne un conseil general non-medical sur un theme (repos,
    hydratation, surveillance, consultation).

    Args:
        topic: theme demande, ex. "repos", "hydratation", "surveillance".
    """
    topic_norm = _strip_accents(topic.lower())
    advices = {
        "repos": "Privilegier le repos et limiter les efforts physiques jusqu'a amelioration.",
        "hydratation": "Boire regulierement de l'eau tout au long de la journee.",
        "surveillance": "Surveiller l'evolution des symptomes (temperature, respiration, etat general) et noter tout changement.",
        "consultation": "Consulter rapidement un medecin en cas d'aggravation ou d'apparition de nouveaux symptomes.",
    }
    for key, value in advices.items():
        if key in topic_norm:
            return value
    return "Aucun conseil specifique trouve pour ce theme. Consultez un medecin en cas de doute."


if __name__ == "__main__":
    mcp.run(transport="stdio")
