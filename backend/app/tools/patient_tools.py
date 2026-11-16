"""
patient_tools.py
-----------------
Tool utilise par le Diagnostic Agent pour interroger le patient.

`ask_patient` declenche une interruption LangGraph (Human-in-the-Loop)
via `interrupt(...)`. Le graphe se met en pause, l'API FastAPI renvoie
la question au frontend, et le frontend renvoie la reponse via
POST /consultation/resume, ce qui reprend l'execution du graphe avec
la reponse du patient injectee dans le state.
"""

from langgraph.types import interrupt
from langchain_core.tools import tool

# Banque de questions standard posees au patient (5 questions obligatoires)
DEFAULT_QUESTIONS = [
    "Quel est le symptome principal qui vous amene aujourd'hui et depuis quand ?",
    "Avez-vous de la fievre ? Si oui, a combien estimez-vous votre temperature ?",
    "Ressentez-vous une douleur ? Si oui, ou se situe-t-elle et comment l'evalueriez-vous sur 10 ?",
    "Avez-vous des difficultes respiratoires, des vertiges ou une perte de connaissance ?",
    "Avez-vous des antecedents medicaux, allergies ou traitements en cours a signaler ?",
]


@tool
def ask_patient(question_index: int) -> str:
    """
    Pose une question au patient (interruption Human-in-the-Loop) et
    retourne la reponse fournie par le patient lors de la reprise du
    graphe.

    Args:
        question_index: index (0-4) de la question a poser dans la
            banque de questions standard.
    """
    question_index = max(0, min(question_index, len(DEFAULT_QUESTIONS) - 1))
    question = DEFAULT_QUESTIONS[question_index]

    # interrupt() suspend le graphe et renvoie `question` a l'appelant
    # (l'API). La reprise se fait avec Command(resume=<reponse patient>).
    patient_answer = interrupt({
        "type": "patient_question",
        "question_index": question_index,
        "question": question,
    })
    return patient_answer


def get_question_text(index: int) -> str:
    """Helper non-tool pour recuperer le texte d'une question par index."""
    index = max(0, min(index, len(DEFAULT_QUESTIONS) - 1))
    return DEFAULT_QUESTIONS[index]


TOTAL_QUESTIONS = len(DEFAULT_QUESTIONS)
