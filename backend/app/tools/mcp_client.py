"""
mcp_client.py
-------------
Client MCP utilise par le Diagnostic Agent pour appeler les outils
exposes par mcp_server/server.py (transport stdio : le client lance le
serveur comme sous-processus, conformement au protocole MCP).

Une couche de repli locale (sans MCP) est fournie au cas ou le serveur
MCP ne serait pas joignable (environnement restreint, paquet `mcp`
absent, etc.), afin que le reste du workflow ne soit jamais bloque.
"""

import asyncio
import os
import sys
import unicodedata

MCP_SERVER_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    "mcp_server",
    "server.py",
)

# Mots-cles de repli (identiques au referentiel MCP) utilises uniquement
# si le serveur MCP n'est pas disponible.
_FALLBACK_RED_FLAGS = [
    "difficulte respiratoire", "essoufflement", "douleur thoracique",
    "perte de connaissance", "confusion", "levres bleues", "fievre 40",
    "saignement important", "vertiges intenses", "douleur 9", "douleur 10",
]


_NEGATION_WORDS = ["pas de", "pas d'", "aucun", "aucune", "sans", " non "]


def _strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(c for c in normalized if not unicodedata.combining(c))


def _is_negated(text: str, keyword: str, window: int = 18) -> bool:
    idx = text.find(keyword)
    if idx == -1:
        return False
    start = max(0, idx - window)
    return any(neg in text[start:idx] for neg in _NEGATION_WORDS)


def _local_fallback_check(symptoms: str) -> dict:
    normalized = _strip_accents(symptoms.lower())
    matches = [
        kw for kw in _FALLBACK_RED_FLAGS
        if kw in normalized and not _is_negated(normalized, kw)
    ]
    return {
        "detected": len(matches) > 0,
        "matches": [{"keyword": m} for m in matches],
        "note": "Verification locale (MCP indisponible).",
    }


async def _call_check_red_flags_async(symptoms: str) -> dict:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    server_params = StdioServerParameters(
        command=sys.executable,
        args=[MCP_SERVER_PATH],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "check_red_flags", arguments={"symptoms": symptoms}
            )
            # Le resultat MCP contient une liste de blocs de contenu ;
            # on recupere le contenu structure si disponible.
            if hasattr(result, "structuredContent") and result.structuredContent:
                return result.structuredContent
            for block in getattr(result, "content", []):
                text = getattr(block, "text", None)
                if text:
                    import json
                    try:
                        return json.loads(text)
                    except Exception:
                        continue
            return _local_fallback_check(symptoms)


def check_red_flags_via_mcp(symptoms: str) -> dict:
    """
    Wrapper synchrone : appelle l'outil MCP `check_red_flags`. Si le
    serveur MCP n'est pas joignable pour une raison quelconque, bascule
    silencieusement sur la verification locale de repli.
    """
    if not symptoms:
        return {"detected": False, "matches": [], "note": "Aucun symptome fourni."}
    try:
        return asyncio.run(_call_check_red_flags_async(symptoms))
    except Exception:
        return _local_fallback_check(symptoms)
