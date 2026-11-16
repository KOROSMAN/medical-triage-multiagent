"""
frontend/app.py
-----------------
Frontend Streamlit du systeme multi-agents d'orientation clinique
preliminaire.

Ecrans (cf. cahier des charges, section 11.1) :
    1. Saisie du cas initial patient
    2. Questions / reponses patient
    3. Revue medecin (traitement / conduite a tenir)
    4. Rapport final

Avertissement permanent : ce systeme est un exercice academique, ne
constitue pas un dispositif medical, et ne remplace pas une
consultation medicale.
"""

import os
import requests
import streamlit as st

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

st.set_page_config(
    page_title="Orientation Clinique Preliminaire",
    page_icon=None,
    layout="centered",
    initial_sidebar_state="expanded",
)

# ----------------------------------------------------------------------
# Theme : palette bleue, typographie "Sora" (titres) + "Inter" (texte)
# ----------------------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sora:wght@500;600;700&family=Inter:wght@400;500;600&display=swap');

    :root {
        --navy: #0B1F3A;
        --blue-deep: #122B52;
        --blue-mid: #1E4FA3;
        --blue-bright: #3D8BFD;
        --blue-pale: #EAF1FC;
        --surface: #F5F8FD;
        --card: #FFFFFF;
        --border: #DCE6F7;
        --text-main: #14213D;
        --text-soft: #51607D;
        --amber: #B7791F;
        --amber-bg: #FFF6E8;
    }

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        color: var(--text-main);
    }

    .stApp {
        background: linear-gradient(180deg, var(--surface) 0%, #EEF3FB 100%);
    }

    h1, h2, h3, h4 {
        font-family: 'Sora', sans-serif !important;
        color: var(--navy) !important;
        letter-spacing: -0.01em;
    }

    section[data-testid="stSidebar"] {
        background: var(--navy);
    }
    section[data-testid="stSidebar"] * {
        color: #DCE6F7 !important;
        font-family: 'Inter', sans-serif;
    }
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: #FFFFFF !important;
        font-family: 'Sora', sans-serif !important;
    }

    .topbar {
        background: linear-gradient(120deg, var(--navy) 0%, var(--blue-mid) 100%);
        border-radius: 16px;
        padding: 28px 32px;
        margin-bottom: 24px;
        box-shadow: 0 10px 30px rgba(11, 31, 58, 0.18);
    }
    .topbar h1 {
        color: #FFFFFF !important;
        margin: 0 0 6px 0;
        font-size: 1.6rem;
    }
    .topbar p {
        color: #CBDCF7;
        margin: 0;
        font-size: 0.92rem;
    }

    .card {
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 24px 26px;
        margin-bottom: 18px;
        box-shadow: 0 4px 14px rgba(20, 33, 61, 0.04);
    }

    .step-pill {
        display: inline-block;
        font-family: 'Sora', sans-serif;
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: var(--blue-mid);
        background: var(--blue-pale);
        border: 1px solid var(--border);
        border-radius: 999px;
        padding: 4px 12px;
        margin-bottom: 10px;
    }

    .disclaimer {
        background: var(--amber-bg);
        border: 1px solid #F0D9A8;
        border-left: 4px solid var(--amber);
        border-radius: 10px;
        padding: 12px 16px;
        font-size: 0.86rem;
        color: #6B4E12;
        margin: 14px 0;
    }

    .qa-line {
        border-bottom: 1px solid var(--border);
        padding: 10px 0;
    }
    .qa-line:last-child { border-bottom: none; }
    .qa-question {
        font-weight: 600;
        color: var(--blue-deep);
        font-size: 0.92rem;
    }
    .qa-answer {
        color: var(--text-soft);
        font-size: 0.92rem;
        margin-top: 2px;
    }

    .redflag-on {
        background: #FDECEC;
        border: 1px solid #F3B9B9;
        color: #8A1F1F;
        border-radius: 10px;
        padding: 10px 14px;
        font-size: 0.88rem;
        font-weight: 500;
    }
    .redflag-off {
        background: #EAF7EE;
        border: 1px solid #BFE3CB;
        color: #1F6B3A;
        border-radius: 10px;
        padding: 10px 14px;
        font-size: 0.88rem;
        font-weight: 500;
    }

    div.stButton > button {
        font-family: 'Sora', sans-serif;
        font-weight: 600;
        background: var(--blue-mid);
        color: #FFFFFF;
        border: none;
        border-radius: 10px;
        padding: 0.55em 1.4em;
        transition: background 0.15s ease;
    }
    div.stButton > button:hover {
        background: var(--blue-bright);
        color: #FFFFFF;
    }

    textarea, input {
        font-family: 'Inter', sans-serif !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

DISCLAIMER_TEXT = (
    "Exercice academique : ce systeme ne constitue pas un dispositif "
    "medical et ne fournit aucun diagnostic definitif. Ce systeme ne "
    "remplace pas une consultation medicale."
)


# ----------------------------------------------------------------------
# Etat de session Streamlit
# ----------------------------------------------------------------------
def init_state():
    defaults = {
        "thread_id": None,
        "screen": 1,
        "status": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_state()


def api_post(path: str, payload: dict) -> dict:
    response = requests.post(f"{BACKEND_URL}{path}", json=payload, timeout=60)
    response.raise_for_status()
    return response.json()


def api_get(path: str) -> dict:
    response = requests.get(f"{BACKEND_URL}{path}", timeout=60)
    response.raise_for_status()
    return response.json()


def refresh_status():
    if st.session_state.thread_id:
        st.session_state.status = api_get(f"/consultation/{st.session_state.thread_id}")


def goto(screen: int):
    st.session_state.screen = screen


def reset_session():
    st.session_state.thread_id = None
    st.session_state.screen = 1
    st.session_state.status = None


# ----------------------------------------------------------------------
# Sidebar : suivi du workflow
# ----------------------------------------------------------------------
with st.sidebar:
    st.markdown("### Suivi de consultation")
    labels = [
        "1. Cas patient",
        "2. Questions patient",
        "3. Revue medecin",
        "4. Rapport final",
    ]
    current = st.session_state.screen
    for i, label in enumerate(labels, start=1):
        marker = "●" if i == current else ("✓" if i < current else "○")
        st.markdown(f"{marker}  {label}")

    st.markdown("---")
    if st.session_state.thread_id:
        st.caption(f"Session : {st.session_state.thread_id[:8]}...")
    st.markdown(
        "<div style='font-size:0.8rem;color:#AFC2E0;margin-top:10px;'>"
        "Backend : " + BACKEND_URL + "</div>",
        unsafe_allow_html=True,
    )
    if st.button("Nouvelle consultation", use_container_width=True):
        reset_session()
        st.rerun()

# ----------------------------------------------------------------------
# Bandeau superieur
# ----------------------------------------------------------------------
st.markdown(
    """
    <div class="topbar">
        <h1>Systeme Multi-Agents d'Orientation Clinique Preliminaire</h1>
        <p>LangGraph &middot; FastAPI &middot; MCP &middot; Human-in-the-Loop</p>
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown(f"<div class='disclaimer'>{DISCLAIMER_TEXT}</div>", unsafe_allow_html=True)


# ----------------------------------------------------------------------
# Ecran 1 : saisie du cas initial patient
# ----------------------------------------------------------------------
def screen_1():
    st.markdown("<span class='step-pill'>Etape 1 / 4</span>", unsafe_allow_html=True)
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("Saisie du cas patient")
    st.write(
        "Decrivez brievement le motif de consultation. Le Diagnostic "
        "Agent posera ensuite 5 questions complementaires."
    )
    patient_case = st.text_area(
        "Cas patient initial",
        placeholder="Exemple : toux et fatigue depuis deux jours, leger mal de gorge...",
        height=120,
    )
    col1, col2 = st.columns([1, 3])
    with col1:
        start_clicked = st.button("Demarrer la consultation")
    st.markdown("</div>", unsafe_allow_html=True)

    if start_clicked:
        if not patient_case.strip():
            st.warning("Veuillez decrire le cas patient avant de continuer.")
            return
        with st.spinner("Initialisation de la session..."):
            session = api_post("/sessions/start", {})
            thread_id = session["thread_id"]
            status = api_post(
                "/consultation/start",
                {"thread_id": thread_id, "patient_case": patient_case},
            )
        st.session_state.thread_id = thread_id
        st.session_state.status = status
        goto(2)
        st.rerun()


# ----------------------------------------------------------------------
# Ecran 2 : questions / reponses patient
# ----------------------------------------------------------------------
def screen_2():
    refresh_status()
    status = st.session_state.status

    st.markdown("<span class='step-pill'>Etape 2 / 4</span>", unsafe_allow_html=True)
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("Questions du Diagnostic Agent")

    qa_history = status.get("qa_history", [])
    if qa_history:
        st.markdown("Reponses deja recueillies :")
        for qa in qa_history:
            st.markdown(
                f"<div class='qa-line'>"
                f"<div class='qa-question'>{qa['question']}</div>"
                f"<div class='qa-answer'>{qa['answer']}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    pending = status.get("pending_interrupt")

    if pending and pending.get("type") == "patient_question":
        st.markdown(f"**Question {pending['question_index'] + 1} / 5**")
        st.markdown(f"{pending['question']}")
        answer = st.text_input("Votre reponse", key=f"answer_{pending['question_index']}")
        if st.button("Envoyer la reponse"):
            if not answer.strip():
                st.warning("Veuillez saisir une reponse.")
            else:
                with st.spinner("Traitement de la reponse..."):
                    status = api_post(
                        "/consultation/resume",
                        {"thread_id": st.session_state.thread_id, "value": answer},
                    )
                st.session_state.status = status
                st.rerun()
    elif pending and pending.get("type") == "physician_review":
        st.success("Les 5 questions ont ete repondues. Synthese clinique generee.")
        if st.button("Passer a la revue medecin"):
            goto(3)
            st.rerun()
    else:
        st.info("En attente de traitement par le Diagnostic Agent...")
        if st.button("Actualiser"):
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# ----------------------------------------------------------------------
# Ecran 3 : revue medecin (Human-in-the-Loop)
# ----------------------------------------------------------------------
def screen_3():
    refresh_status()
    status = st.session_state.status
    pending = status.get("pending_interrupt")

    st.markdown("<span class='step-pill'>Etape 3 / 4 &middot; Human-in-the-Loop</span>", unsafe_allow_html=True)
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("Revue du medecin traitant")

    if pending and pending.get("type") == "physician_review":
        st.markdown("**Synthese clinique preliminaire**")
        st.write(pending.get("diagnostic_summary", ""))

        st.markdown("**Recommandation intermediaire**")
        st.write(pending.get("interim_care", ""))

        if pending.get("red_flags_detected"):
            st.markdown(
                "<div class='redflag-on'>Signes d'alerte detectes : orientation rapide recommandee.</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<div class='redflag-off'>Aucun signe d'alerte majeur detecte.</div>",
                unsafe_allow_html=True,
            )

        st.markdown("---")
        st.markdown("**Decision du medecin traitant**")
        treatment = st.text_area(
            "Traitement propose ou conduite a tenir",
            placeholder="Exemple : repos, paracetamol si besoin, controle si persistance au-dela de 5 jours...",
            height=120,
        )
        if st.button("Valider la revue medecin"):
            if not treatment.strip():
                st.warning("Veuillez saisir une decision avant de valider.")
            else:
                with st.spinner("Generation du rapport final..."):
                    status = api_post(
                        "/consultation/resume",
                        {"thread_id": st.session_state.thread_id, "value": treatment},
                    )
                st.session_state.status = status
                goto(4)
                st.rerun()
    elif status.get("final_report"):
        st.success("La revue medecin a deja ete validee.")
        if st.button("Voir le rapport final"):
            goto(4)
            st.rerun()
    else:
        st.info("En attente de la synthese clinique du Diagnostic Agent.")
        if st.button("Retour aux questions patient"):
            goto(2)
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# ----------------------------------------------------------------------
# Ecran 4 : rapport final
# ----------------------------------------------------------------------
def screen_4():
    refresh_status()
    status = st.session_state.status

    st.markdown("<span class='step-pill'>Etape 4 / 4</span>", unsafe_allow_html=True)
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("Rapport final")

    final_report = status.get("final_report")
    if final_report:
        st.text(final_report)
        st.download_button(
            "Telecharger le rapport (.txt)",
            data=final_report,
            file_name="rapport_orientation_clinique.txt",
            mime="text/plain",
        )
        st.markdown(
            f"<div class='disclaimer'>{DISCLAIMER_TEXT}</div>",
            unsafe_allow_html=True,
        )
    else:
        st.info("Le rapport final n'est pas encore disponible.")
        if st.button("Retour a la revue medecin"):
            goto(3)
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# ----------------------------------------------------------------------
# Routage des ecrans
# ----------------------------------------------------------------------
if st.session_state.thread_id is None:
    screen_1()
else:
    screen = st.session_state.screen
    if screen == 2:
        screen_2()
    elif screen == 3:
        screen_3()
    elif screen == 4:
        screen_4()
    else:
        screen_2()
