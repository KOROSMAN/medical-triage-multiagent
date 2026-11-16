"""
report_agent.py
-----------------
Genere le rapport final structure, en combinant la synthese clinique
preliminaire, la recommandation intermediaire et la decision du
medecin traitant.

Le rapport final mentionne TOUJOURS, explicitement et de maniere non
modifiable, la phrase obligatoire :
    "Ce systeme ne remplace pas une consultation medicale."
"""

import datetime

from app.state import MedicalState
from app.llm import generate_text

MANDATORY_DISCLAIMER = "Ce systeme ne remplace pas une consultation medicale."


def _build_report_fallback(state: MedicalState) -> str:
    qa_lines = "\n".join(
        f"  - {qa['question']} -> {qa['answer']}"
        for qa in state.get("qa_history", [])
    )
    return f"""RAPPORT D'ORIENTATION CLINIQUE PRELIMINAIRE
(Exercice academique - aucun caractere de dispositif medical)
Genere le : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}

1. Cas patient initial
   {state.get('patient_case', 'Non precise')}

2. Questions / reponses patient
{qa_lines if qa_lines else '   Aucune'}

3. Synthese clinique preliminaire
   {state.get('diagnostic_summary', 'Non disponible')}

4. Signes d'alerte detectes
   {"Oui" if state.get('red_flags_detected') else "Non"}

5. Recommandation intermediaire
   {state.get('interim_care', 'Non disponible')}

6. Avis et conduite a tenir du medecin traitant
   {state.get('physician_treatment', 'Non disponible')}

7. Avertissement
   {MANDATORY_DISCLAIMER}
"""


def report_agent(state: MedicalState) -> dict:
    prompt = (
        "Redige un rapport final structure (sections numerotees) a partir des "
        "elements suivants, en restant dans le cadre d'une orientation clinique "
        f"preliminaire : cas patient = {state.get('patient_case', '')} ; "
        f"synthese = {state.get('diagnostic_summary', '')} ; "
        f"recommandation intermediaire = {state.get('interim_care', '')} ; "
        f"avis medecin = {state.get('physician_treatment', '')}. "
        "Termine OBLIGATOIREMENT par la phrase exacte : "
        f"\"{MANDATORY_DISCLAIMER}\""
    )
    fallback_report = _build_report_fallback(state)
    final_report = generate_text(prompt, fallback=fallback_report)

    # Garde-fou : on s'assure que la phrase obligatoire est toujours
    # presente dans le rapport, meme si elle provient d'un vrai LLM.
    if MANDATORY_DISCLAIMER not in final_report:
        final_report = final_report.rstrip() + "\n\n" + MANDATORY_DISCLAIMER

    return {
        "final_report": final_report,
        "next": "FINISH",
    }
