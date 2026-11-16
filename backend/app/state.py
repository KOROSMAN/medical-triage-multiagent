"""
state.py
--------
Etat partage du graphe LangGraph (MedicalState).

IMPORTANT (cadre ethique du projet) :
Ce systeme est un exercice academique. Il ne constitue pas un dispositif
medical et ne fournit aucun diagnostic definitif. Les sorties produites
sont des "orientations cliniques preliminaires" / "syntheses cliniques" /
"recommandations intermediaires" qui doivent toujours etre validees par
un medecin traitant (etape Human-in-the-Loop obligatoire du workflow).
"""

from typing import Annotated, List, Optional
from typing_extensions import TypedDict, Literal

from langgraph.graph.message import add_messages


class PatientQA(TypedDict):
    """Une question posee au patient et sa reponse."""
    question: str
    answer: str


class MedicalState(TypedDict, total=False):
    # Historique conversationnel (utilise par add_messages pour le merge)
    messages: Annotated[list, add_messages]

    # Routage decide par le Supervisor
    next: Literal[
        "diagnostic_agent",
        "physician_review",
        "report_agent",
        "FINISH",
    ]

    # --- Cas patient initial ---
    patient_case: str

    # --- Interaction patient (Diagnostic Agent / tool ask_patient) ---
    question_count: int
    qa_history: List[PatientQA]

    # --- Sorties du Diagnostic Agent ---
    diagnostic_summary: str
    interim_care: str
    red_flags_detected: bool
    red_flags_details: Optional[str]

    # --- Revue medecin (Human-in-the-Loop) ---
    physician_treatment: str
    physician_validated: bool

    # --- Rapport final ---
    final_report: str

    # --- Identifiant de session/thread ---
    thread_id: str
