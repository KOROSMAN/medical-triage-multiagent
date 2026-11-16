"""
graph.py
---------
Construction du graphe LangGraph multi-agents :

    START -> supervisor -> diagnostic_agent -> supervisor
          -> physician_review -> supervisor -> report_agent
          -> supervisor -> END

Le Supervisor est appele apres chaque agent et decide, via
`route_from_supervisor`, de l'etape suivante en fonction du state.

Un `MemorySaver` (checkpointer en memoire) est utilise pour permettre
les interruptions Human-in-the-Loop (patient + medecin) et la reprise
de session via `thread_id` (necessaire pour LangGraph Studio et pour
l'API FastAPI : POST /consultation/resume).
"""

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from app.state import MedicalState
from app.nodes.supervisor import supervisor, route_from_supervisor
from app.nodes.diagnostic_agent import diagnostic_agent
from app.nodes.physician_review import physician_review
from app.nodes.report_agent import report_agent


def build_graph(checkpointer=None):
    """Construit (et compile) le graphe. Permet d'injecter un
    checkpointer different (utile pour les tests)."""
    workflow = StateGraph(MedicalState)

    workflow.add_node("supervisor", supervisor)
    workflow.add_node("diagnostic_agent", diagnostic_agent)
    workflow.add_node("physician_review", physician_review)
    workflow.add_node("report_agent", report_agent)

    workflow.add_edge(START, "supervisor")

    workflow.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {
            "diagnostic_agent": "diagnostic_agent",
            "physician_review": "physician_review",
            "report_agent": "report_agent",
            "FINISH": END,
        },
    )

    workflow.add_edge("diagnostic_agent", "supervisor")
    workflow.add_edge("physician_review", "supervisor")
    workflow.add_edge("report_agent", "supervisor")

    if checkpointer is None:
        checkpointer = MemorySaver()

    return workflow.compile(checkpointer=checkpointer)


# Instance par defaut utilisee par l'API FastAPI et par LangGraph Studio
# (reference dans backend/langgraph.json).
graph = build_graph()
