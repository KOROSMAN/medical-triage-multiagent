"""
api.py
-------
API FastAPI exposant le graphe LangGraph multi-agents.

Endpoints obligatoires (cf. cahier des charges, section 10) :
    POST /sessions/start
    POST /consultation/start
    POST /consultation/resume
    GET  /consultation/{thread_id}
    GET  /consultation/{thread_id}/report

Le HITL (patient + medecin) est gere via les interruptions LangGraph :
chaque appel qui declenche un `interrupt()` cote graphe est restitue au
frontend sous forme de "pending_interrupt" ; le frontend renvoie la
reponse via /consultation/resume pour faire reprendre le graphe.
"""

import uuid
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langgraph.types import Command

from app.graph import graph

app = FastAPI(
    title="Systeme multi-agents d'orientation clinique preliminaire",
    description=(
        "API pedagogique LangGraph. Ce systeme ne constitue pas un "
        "dispositif medical et ne fournit pas de diagnostic definitif. "
        "Ce systeme ne remplace pas une consultation medicale."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registre simple des sessions connues (en complement du checkpointer
# LangGraph, qui conserve l'etat reel par thread_id).
_KNOWN_SESSIONS: set[str] = set()


class StartSessionResponse(BaseModel):
    thread_id: str


class StartConsultationRequest(BaseModel):
    thread_id: str
    patient_case: str


class ResumeConsultationRequest(BaseModel):
    thread_id: str
    value: str


def _config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def _extract_pending_interrupt(thread_id: str) -> Optional[dict]:
    """Inspecte l'etat courant du graphe pour ce thread et retourne
    le contenu de l'interruption en attente, s'il y en a une.

    Note : on se base directement sur `state.tasks[*].interrupts` plutot
    que sur `state.next`, car ce dernier peut etre vide alors qu'une
    tache avec une interruption est bien en attente (comportement
    observe avec les interruptions multiples dans un meme noeud)."""
    state = graph.get_state(_config(thread_id))
    for task in state.tasks:
        if task.interrupts:
            return task.interrupts[0].value
    return None


def _has_pending_interrupt(thread_id: str) -> bool:
    return _extract_pending_interrupt(thread_id) is not None


def _build_status_response(thread_id: str) -> dict:
    state = graph.get_state(_config(thread_id))
    pending_interrupt = _extract_pending_interrupt(thread_id)
    values = state.values or {}
    return {
        "thread_id": thread_id,
        "is_finished": pending_interrupt is None and bool(values.get("final_report")),
        "pending_interrupt": pending_interrupt,
        "question_count": values.get("question_count", 0),
        "qa_history": values.get("qa_history", []),
        "diagnostic_summary": values.get("diagnostic_summary"),
        "interim_care": values.get("interim_care"),
        "red_flags_detected": values.get("red_flags_detected"),
        "physician_treatment": values.get("physician_treatment"),
        "final_report": values.get("final_report"),
    }


@app.post("/sessions/start", response_model=StartSessionResponse)
def start_session() -> StartSessionResponse:
    """Cree un nouveau thread_id de session (Ecran 1 du frontend)."""
    thread_id = str(uuid.uuid4())
    _KNOWN_SESSIONS.add(thread_id)
    return StartSessionResponse(thread_id=thread_id)


@app.post("/consultation/start")
def start_consultation(req: StartConsultationRequest) -> dict:
    """Demarre le graphe pour un cas patient initial. Retourne la
    premiere interruption (premiere question au patient)."""
    _KNOWN_SESSIONS.add(req.thread_id)
    initial_state = {
        "patient_case": req.patient_case,
        "qa_history": [],
        "thread_id": req.thread_id,
    }
    graph.invoke(initial_state, config=_config(req.thread_id))
    return _build_status_response(req.thread_id)


@app.post("/consultation/resume")
def resume_consultation(req: ResumeConsultationRequest) -> dict:
    """Reprend le graphe apres une interruption (reponse patient ou
    decision du medecin traitant)."""
    if req.thread_id not in _KNOWN_SESSIONS:
        raise HTTPException(status_code=404, detail="Session inconnue.")

    if not _has_pending_interrupt(req.thread_id):
        raise HTTPException(
            status_code=400,
            detail="Aucune interruption en attente pour cette session.",
        )

    graph.invoke(Command(resume=req.value), config=_config(req.thread_id))
    return _build_status_response(req.thread_id)


@app.get("/consultation/{thread_id}")
def get_consultation(thread_id: str) -> dict:
    """Retourne l'etat courant de la consultation (utilise pour le
    polling/affichage frontend a tout moment)."""
    if thread_id not in _KNOWN_SESSIONS:
        raise HTTPException(status_code=404, detail="Session inconnue.")
    return _build_status_response(thread_id)


@app.get("/consultation/{thread_id}/report")
def get_report(thread_id: str) -> dict:
    """Retourne le rapport final structure, une fois disponible."""
    if thread_id not in _KNOWN_SESSIONS:
        raise HTTPException(status_code=404, detail="Session inconnue.")
    status = _build_status_response(thread_id)
    if not status.get("final_report"):
        raise HTTPException(
            status_code=202,
            detail="Le rapport final n'est pas encore disponible.",
        )
    return {
        "thread_id": thread_id,
        "final_report": status["final_report"],
        "disclaimer": "Ce systeme ne remplace pas une consultation medicale.",
    }


@app.get("/")
def root() -> dict:
    return {
        "status": "ok",
        "message": "API du systeme multi-agents d'orientation clinique preliminaire.",
        "disclaimer": "Ce systeme ne remplace pas une consultation medicale.",
    }
