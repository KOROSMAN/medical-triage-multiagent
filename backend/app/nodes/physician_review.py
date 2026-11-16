"""
physician_review.py
---------------------
Etape Human-in-the-Loop OBLIGATOIRE representant le medecin traitant.

Le medecin recoit la synthese clinique preliminaire et la
recommandation intermediaire, puis propose un traitement ou une
conduite a tenir avant que le rapport final ne soit genere.
"""

from langgraph.types import interrupt

from app.state import MedicalState


def physician_review(state: MedicalState) -> dict:
    review_payload = {
        "type": "physician_review",
        "patient_case": state.get("patient_case", ""),
        "diagnostic_summary": state.get("diagnostic_summary", ""),
        "interim_care": state.get("interim_care", ""),
        "red_flags_detected": state.get("red_flags_detected", False),
        "qa_history": state.get("qa_history", []),
    }

    # Interruption : le graphe se met en pause et attend la decision du
    # medecin traitant (reprise via POST /consultation/resume).
    physician_input = interrupt(review_payload)

    return {
        "physician_treatment": physician_input,
        "physician_validated": True,
        "next": "report_agent",
    }
