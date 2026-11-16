"""
supervisor.py
--------------
Le Supervisor orchestre le workflow : il decide de l'etape suivante en
fonction de ce qui a deja ete produit dans le state partage.

Ordre du workflow minimal attendu :
    START -> Supervisor -> DiagnosticAgent -> Supervisor
           -> PhysicianReview -> Supervisor -> ReportAgent -> Supervisor -> END
"""

from app.state import MedicalState


def supervisor(state: MedicalState) -> dict:
    """Determine la prochaine etape du workflow et la place dans `next`."""

    if not state.get("diagnostic_summary"):
        decision = "diagnostic_agent"
    elif not state.get("physician_treatment"):
        decision = "physician_review"
    elif not state.get("final_report"):
        decision = "report_agent"
    else:
        decision = "FINISH"

    return {"next": decision}


def route_from_supervisor(state: MedicalState) -> str:
    """Fonction de routage utilisee par les conditional edges du graphe."""
    return state.get("next", "FINISH")
