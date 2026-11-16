"""
llm.py
------
Petit wrapper autour du LLM utilise par les agents.

Si la variable d'environnement ANTHROPIC_API_KEY est definie, on utilise
un vrai modele Claude via langchain_anthropic. Sinon, on bascule sur un
generateur "mock" base sur des regles simples, ce qui permet de faire
tourner et de tester tout le graphe (et l'API) hors-ligne, sans cle.

Cela respecte la consigne pedagogique : le systeme ne doit jamais
produire de diagnostic definitif, qu'il soit gere par un vrai LLM ou
par le mode mock.
"""

import os

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

_SYSTEM_GUARD = (
    "Tu es un assistant pedagogique d'orientation clinique PRELIMINAIRE. "
    "Tu ne dois JAMAIS poser de diagnostic definitif. Utilise uniquement "
    "les termes : orientation clinique preliminaire, synthese clinique, "
    "recommandation intermediaire. Rappelle que ce systeme ne remplace pas "
    "une consultation medicale."
)


def _get_chat_model():
    """Retourne une instance ChatAnthropic si une cle API est disponible."""
    if not ANTHROPIC_API_KEY:
        return None
    try:
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model="claude-sonnet-4-6", temperature=0.2)
    except Exception:
        return None


def generate_text(prompt: str, fallback: str) -> str:
    """
    Tente de generer du texte avec le LLM reel. En cas d'absence de cle,
    d'erreur reseau ou d'exception quelconque, retourne le texte de repli
    (fallback) construit de maniere deterministe par l'agent appelant.
    """
    model = _get_chat_model()
    if model is None:
        return fallback
    try:
        from langchain_core.messages import SystemMessage, HumanMessage
        response = model.invoke([
            SystemMessage(content=_SYSTEM_GUARD),
            HumanMessage(content=prompt),
        ])
        text = getattr(response, "content", None)
        if isinstance(text, str) and text.strip():
            return text.strip()
        return fallback
    except Exception:
        return fallback


def is_live_mode() -> bool:
    """Indique si un vrai LLM est configure (utile pour les logs/UI)."""
    return ANTHROPIC_API_KEY is not None
