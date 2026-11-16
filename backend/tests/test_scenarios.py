"""
tests/test_scenarios.py
-------------------------
Couvre les 3 jeux de tests attendus (cahier des charges, section 13) :
    - Cas 1 : syndrome respiratoire simple (sans red flag)
    - Cas 2 : cas avec red flags
    - Cas 3 : cas benin

Pour chaque scenario, on verifie : les 5 questions sont posees, une
recommandation intermediaire est generee, la revue medecin est
obligatoire, et le rapport final contient la mention legale
obligatoire.

Execution :
    cd backend
    python -m pytest tests/test_scenarios.py -v
    (ou directement : python tests/test_scenarios.py)
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from app.graph import build_graph


def _run_scenario(thread_id: str, patient_case: str, answers: list, physician_input: str):
    graph = build_graph(MemorySaver())
    config = {"configurable": {"thread_id": thread_id}}

    graph.invoke(
        {"patient_case": patient_case, "qa_history": [], "thread_id": thread_id},
        config=config,
    )

    for answer in answers:
        graph.invoke(Command(resume=answer), config=config)

    state = graph.get_state(config)
    assert state.values.get("question_count") == 5, "Les 5 questions doivent etre posees."
    assert state.values.get("diagnostic_summary"), "Une synthese clinique doit etre produite."
    assert state.values.get("interim_care"), "Une recommandation intermediaire doit etre produite."

    graph.invoke(Command(resume=physician_input), config=config)
    state = graph.get_state(config)

    assert state.values.get("physician_treatment") == physician_input
    assert state.values.get("final_report"), "Le rapport final doit etre genere."
    assert "Ce systeme ne remplace pas une consultation medicale." in state.values["final_report"]

    return state.values


def test_case_1_syndrome_respiratoire_simple():
    values = _run_scenario(
        thread_id="case-1",
        patient_case="Toux et leger mal de gorge depuis 2 jours",
        answers=[
            "Toux seche depuis 2 jours",
            "Pas de fievre",
            "Leger mal de gorge, 2 sur 10",
            "Pas de difficulte respiratoire",
            "Aucun antecedent",
        ],
        physician_input="Repos, surveillance, paracetamol si besoin.",
    )
    assert values.get("red_flags_detected") is False
    print("Cas 1 OK - aucun red flag detecte.")


def test_case_2_avec_red_flags():
    values = _run_scenario(
        thread_id="case-2",
        patient_case="Malaise brutal avec essoufflement",
        answers=[
            "Malaise depuis ce matin",
            "Fievre a 39.5",
            "Douleur thoracique forte, 8 sur 10",
            "Difficulte respiratoire importante",
            "Aucun antecedent",
        ],
        physician_input="Orientation immediate vers les urgences.",
    )
    assert values.get("red_flags_detected") is True
    print("Cas 2 OK - red flags correctement detectes.")


def test_case_3_benin():
    values = _run_scenario(
        thread_id="case-3",
        patient_case="Fatigue legere en fin de semaine",
        answers=[
            "Fatigue legere depuis 1 jour",
            "Pas de fievre",
            "Pas de douleur",
            "Pas de difficulte respiratoire",
            "Aucun antecedent",
        ],
        physician_input="Aucun traitement necessaire, repos conseille.",
    )
    assert values.get("red_flags_detected") is False
    print("Cas 3 OK - cas benin correctement gere.")


if __name__ == "__main__":
    test_case_1_syndrome_respiratoire_simple()
    test_case_2_avec_red_flags()
    test_case_3_benin()
    print("\nTous les scenarios sont passes avec succes.")
