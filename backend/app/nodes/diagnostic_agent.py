"""
diagnostic_agent.py
--------------------
Agent qui :
1. Pose 5 questions successives au patient via le tool `ask_patient`
   (chaque question declenche une interruption Human-in-the-Loop ;
   les 5 interruptions sont gerees dans une seule execution de noeud,
   pattern standard LangGraph de "multiples interrupts par noeud").
2. Verifie les signes d'alerte (red flags) via l'outil MCP.
3. Produit une synthese clinique PRELIMINAIRE (jamais un diagnostic
   definitif).
4. Produit une recommandation intermediaire via le tool
   `recommend_interim_care`.
"""

import json

from app.state import MedicalState
from app.llm import generate_text
from app.tools.patient_tools import ask_patient, get_question_text, TOTAL_QUESTIONS
from app.tools.care_tools import recommend_interim_care
from app.tools.mcp_client import check_red_flags_via_mcp


def _build_summary_fallback(patient_case: str, qa_history: list, red_flags_detected: bool) -> str:
    lines = [
        "Synthese clinique preliminaire (exercice academique - ne remplace pas une consultation medicale).",
        f"Motif initial rapporte : {patient_case or 'non precise'}.",
    ]
    for qa in qa_history:
        lines.append(f"- {qa['question']} => {qa['answer']}")
    if red_flags_detected:
        lines.append(
            "Des signes d'alerte ont ete identifies dans les reponses du "
            "patient : une orientation rapide vers un medecin est conseillee."
        )
    else:
        lines.append(
            "Aucun signe d'alerte majeur identifie dans les reponses "
            "fournies, sur la base des elements rapportes."
        )
    return "\n".join(lines)


def diagnostic_agent(state: MedicalState) -> dict:
    qa_history = list(state.get("qa_history", []))

    # Boucle obligatoire : 5 questions successives gerees via le tool.
    for index in range(TOTAL_QUESTIONS):
        if index < len(qa_history):
            continue
        question_text = get_question_text(index)
        answer = ask_patient.invoke({"question_index": index})
        qa_history.append({"question": question_text, "answer": answer})

    patient_case = state.get("patient_case", "")
    symptoms_text = patient_case + " | " + " | ".join(qa["answer"] for qa in qa_history)

    # Outil MCP obligatoire : verification des signes d'alerte.
    red_flag_result = check_red_flags_via_mcp(symptoms_text)
    red_flags_detected = bool(red_flag_result.get("detected", False))

    prompt = (
        "A partir du cas patient et des 5 questions/reponses suivantes, redige "
        "une SYNTHESE CLINIQUE PRELIMINAIRE courte et prudente (pas de diagnostic "
        "definitif). Cas initial: " + patient_case + "\n" +
        "\n".join(f"Q: {qa['question']}\nR: {qa['answer']}" for qa in qa_history)
    )
    fallback_summary = _build_summary_fallback(patient_case, qa_history, red_flags_detected)
    diagnostic_summary = generate_text(prompt, fallback=fallback_summary)

    interim_care = recommend_interim_care.invoke({"red_flags_detected": red_flags_detected})

    return {
        "qa_history": qa_history,
        "question_count": len(qa_history),
        "diagnostic_summary": diagnostic_summary,
        "interim_care": interim_care,
        "red_flags_detected": red_flags_detected,
        "red_flags_details": json.dumps(red_flag_result.get("matches", []), ensure_ascii=False),
        "next": "physician_review",
    }
