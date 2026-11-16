"""
care_tools.py
--------------
Tool produisant une recommandation intermediaire PRUDENTE, qui ne
remplace jamais l'avis du medecin traitant.
"""

from langchain_core.tools import tool


@tool
def recommend_interim_care(red_flags_detected: bool) -> str:
    """
    Genere une recommandation intermediaire generale et prudente, a
    partir de la presence ou non de signes d'alerte (red flags).

    Args:
        red_flags_detected: True si des signes d'alerte ont ete detectes
            (via l'outil MCP de verification des red flags).
    """
    if red_flags_detected:
        return (
            "Recommandation intermediaire (prudence renforcee) : des signes "
            "d'alerte ont ete identifies. Il est recommande de consulter "
            "rapidement un medecin ou de vous rendre aux urgences en cas "
            "d'aggravation. En attendant : repos, hydratation reguliere, "
            "surveillance rapprochee des symptomes (temperature, respiration, "
            "etat general)."
        )
    return (
        "Recommandation intermediaire generale : repos, bonne hydratation, "
        "surveillance de l'evolution des symptomes sur 24 a 48h. Consultez "
        "rapidement un medecin en cas d'aggravation, d'apparition de fievre "
        "elevee, de difficultes respiratoires ou de tout autre signe "
        "inhabituel. Cette recommandation reste generale et ne remplace pas "
        "l'avis du medecin traitant."
    )
