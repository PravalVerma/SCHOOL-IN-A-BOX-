import tempfile
from pathlib import Path

import streamlit as st
import requests

from services.ingestion import ingest_pdf  # still local for now
from services.ocr import extract_text_from_image
from services.users import ensure_user, get_all_user_ids


BACKEND_URL = "http://localhost:8000"


# ---------- Session helpers ----------

def set_current_quiz(quiz_id: str, mcqs: list[dict]) -> None:
    """Store current quiz info in session_state for answering."""
    st.session_state["current_quiz_id"] = quiz_id
    st.session_state["current_quiz_mcqs"] = mcqs
    st.session_state["quiz_submitted"] = False


def get_current_quiz():
    """Return (quiz_id, mcq_dict_list) or (None, None) if no quiz."""
    quiz_id = st.session_state.get("current_quiz_id")
    mcqs = st.session_state.get("current_quiz_mcqs")
    if not quiz_id or not mcqs:
        return None, None
    return quiz_id, mcqs


# ---------- Streamlit UI ----------

st.set_page_config(page_title="School in a Box", layout="wide")
st.title("📦 School in a Box")

# --- Session init ---
if "user_id" not in st.session_state:
    st.session_state["user_id"] = "demo-user"

# --- Sidebar: switch user ---

st.sidebar.markdown("### 👤 User")

existing_users = get_all_user_ids()
default_user = st.session_state["user_id"]

selected_user = st.sidebar.selectbox(
    "Existing users",
    options=["(New user)"] + existing_users,
    index=1 if default_user in existing_users else 0,
    key="selected_user_select",
)

new_user_input = st.sidebar.text_input(
    "New user ID (if creating one)",
    value="" if default_user in existing_users else default_user,
    key="new_user_id_input",
)

if st.sidebar.button("Use this user", key="btn_switch_user"):
    if new_user_input.strip():
        st.session_state["user_id"] = new_user_input.strip()
        ensure_user(st.session_state["user_id"])
        if hasattr(st, "rerun"):
            st.rerun()
        else:
            st.rerun()
    elif selected_user != "(New user)":
        st.session_state["user_id"] = selected_user
        ensure_user(st.session_state["user_id"])
        if hasattr(st, "rerun"):
            st.rerun()
        else:
            st.rerun()

st.sidebar.markdown(f"**Current user:** `{st.session_state['user_id']}`")

tab_learn, tab_quiz, tab_coach = st.tabs(["📘 Learn", "📝 Quiz", "🎯 Coach"])


# ---------- LEARN TAB ----------

with tab_learn:
    st.header("Learn")

    st.subheader("Ingest Content")

    col1, col2, col3 = st.columns(3)

    # --- Text ingestion via backend ---
    with col1:
        st.markdown("**Paste Text**")
        text_source_id = st.text_input(
            "Text Source ID (e.g., 'physics_ch1_notes')",
            value="text_source_1",
            key="text_source_id",
        )
        raw_text = st.text_area(
            "Content to ingest",
            height=200,
            key="learn_raw_text",
        )
        if st.button("Ingest Text", key="btn_ingest_text") and raw_text.strip():
            try:
                resp = requests.post(
                    f"{BACKEND_URL}/ingest/text",
                    json={"text": raw_text, "source_id": text_source_id},
                    timeout=60,
                )
                data = resp.json()
                num_chunks = data.get("num_chunks", 0)
                st.success(f"Ingested {num_chunks} chunks from text via backend.")
            except Exception as e:
                st.error(f"Error calling backend /ingest/text: {e}")

    # --- PDF ingestion (still local pipeline) ---
    with col2:
        st.markdown("**Upload PDF**")
        pdf_file = st.file_uploader(
            "Upload a PDF",
            type=["pdf"],
            key="learn_pdf_file",
        )
        pdf_source_id = st.text_input(
            "PDF Source ID (e.g., 'physics_ch1_pdf')",
            value="pdf_source_1",
            key="pdf_source_id",
        )

        if st.button("Ingest PDF", key="btn_ingest_pdf") and pdf_file is not None:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(pdf_file.read())
                tmp_path = tmp.name

            # Uses local ingestion pipeline for now
            chunks = ingest_pdf(tmp_path, source_id=pdf_source_id)
            st.success(f"Ingested {len(chunks)} chunks from PDF: {pdf_file.name}")

    # --- Image ingestion via OCR + backend text ingest ---
    with col3:
        st.markdown("**Upload Image (OCR)**")
        image_file = st.file_uploader(
            "Upload an image",
            type=["png", "jpg", "jpeg"],
            key="learn_image_file",
        )
        image_source_id = st.text_input(
            "Image Source ID (e.g., 'physics_ch1_image')",
            value="image_source_1",
            key="image_source_id",
        )

        if st.button("Run OCR", key="btn_run_ocr") and image_file is not None:
            image_bytes = image_file.read()
            with st.spinner("Running OCR..."):
                extracted_text = extract_text_from_image(image_bytes)
            if not extracted_text.strip():
                st.warning("No text detected in the image.")
            else:
                st.text_area(
                    "Extracted text (you can edit before ingesting if needed)",
                    value=extracted_text,
                    height=150,
                    key="ocr_extracted_text_preview",
                )

        if st.button("Ingest Extracted Text", key="btn_ingest_extracted_text"):
            ocr_text = st.session_state.get("ocr_extracted_text_preview", "")
            if not ocr_text.strip():
                st.warning("No OCR text available to ingest.")
            else:
                try:
                    resp = requests.post(
                        f"{BACKEND_URL}/ingest/text",
                        json={"text": ocr_text, "source_id": image_source_id},
                        timeout=60,
                    )
                    data = resp.json()
                    num_chunks = data.get("num_chunks", 0)
                    st.success(f"OCR done and ingested {num_chunks} chunks via backend.")
                except Exception as e:
                    st.error(f"Error calling backend /ingest/text: {e}")

    st.markdown("---")
    st.subheader("Explain Content")

    explain_mode = st.radio(
        "Explanation mode",
        ["Explain pasted text", "Explain using stored material (RAG)"],
        key="explain_mode",
    )

    explain_level = st.selectbox(
        "Explanation level",
        ["simple", "intermediate", "advanced"],
        index=0,
        key="explain_level",
    )

    if explain_mode == "Explain pasted text":
        explain_text = st.text_area(
            "Text to explain",
            height=180,
            key="explain_raw_text_area",
        )
        if st.button("Explain Text", key="btn_explain_text") and explain_text.strip():
            with st.spinner("Calling backend /explain/raw..."):
                try:
                    resp = requests.post(
                        f"{BACKEND_URL}/explain/raw",
                        json={"text": explain_text, "level": explain_level},
                        timeout=120,
                    )
                    data = resp.json()
                    explanation = data.get("explanation", "")
                    st.markdown("### Explanation")
                    st.write(explanation)
                except Exception as e:
                    st.error(f"Error calling backend /explain/raw: {e}")

    else:
        question = st.text_input(
            "Ask a question based on your ingested material",
            key="explain_question",
        )
        if st.button("Explain from Stored Material", key="btn_explain_rag") and question.strip():
            with st.spinner("Calling backend /explain/rag..."):
                try:
                    resp = requests.post(
                        f"{BACKEND_URL}/explain/rag",
                        json={"question": question, "level": explain_level, "k": 5},
                        timeout=120,
                    )
                    data = resp.json()
                    explanation = data.get("explanation", "")
                    st.markdown("### Explanation from Stored Material")
                    st.write(explanation)
                except Exception as e:
                    st.error(f"Error calling backend /explain/rag: {e}")


# ---------- QUIZ TAB ----------

with tab_quiz:
    st.header("Quiz")

    st.subheader("Generate a Quiz")

    topic_or_question = st.text_input(
        "Topic or question to generate quiz from (will use stored material if available)",
        key="quiz_topic",
    )
    num_questions = st.number_input(
        "Number of questions",
        min_value=1,
        max_value=20,
        value=5,
        step=1,
        key="quiz_num_questions",
    )
    difficulty = st.selectbox(
        "Difficulty",
        ["easy", "medium", "hard"],
        index=1,
        key="quiz_difficulty",
    )
    source_id_for_quiz = st.text_input(
        "Source ID for this quiz (e.g., 'physics_ch1_pdf')",
        value="generic_source",
        key="quiz_source_id",
    )

    if st.button("Generate Quiz", key="btn_generate_quiz") and topic_or_question.strip():
        with st.spinner("Calling backend /quiz/generate..."):
            try:
                resp = requests.post(
                    f"{BACKEND_URL}/quiz/generate",
                    json={
                        "user_id": st.session_state["user_id"],
                        "topic_or_question": topic_or_question,
                        "source_id": source_id_for_quiz,
                        "num_questions": int(num_questions),
                        "difficulty": difficulty,
                        "k": 5,
                    },
                    timeout=180,
                )
                data = resp.json()
                quiz_id = data.get("quiz_id")
                mcqs = data.get("mcqs", [])

                if not quiz_id or not mcqs:
                    st.error("Backend returned no quiz. Try again or adjust the input.")
                else:
                    # mcqs is already a list of dicts from backend
                    set_current_quiz(quiz_id, mcqs)
                    st.success(f"Quiz generated and saved. Quiz ID: {quiz_id}")

            except Exception as e:
                st.error(f"Error calling backend /quiz/generate: {e}")

    st.markdown("---")
    st.subheader("Answer Current Quiz")

    quiz_id, mcq_dicts = get_current_quiz()

    if not quiz_id or not mcq_dicts:
        st.info("No current quiz. Generate a quiz above to start.")
    else:
        st.write(f"**Current Quiz ID:** `{quiz_id}`")

        # Render questions with options
        for i, mcq in enumerate(mcq_dicts):
            st.markdown(f"**Q{i+1}. {mcq['question']}**")
            selected = st.radio(
                "Select an option",
                options=list(range(len(mcq["options"]))),
                format_func=lambda idx, opts=mcq["options"]: f"{chr(65+idx)}. {opts[idx]}",
                key=f"quiz_q_{i}_choice",
            )
            st.markdown("---")

        if st.button("Submit Answers", key="btn_submit_quiz"):
            total = len(mcq_dicts)
            correct_count = 0

            for i, mcq in enumerate(mcq_dicts):
                chosen_index = st.session_state.get(f"quiz_q_{i}_choice", 0)
                correct_index = mcq["correct_index"]
                is_correct = (chosen_index == correct_index)

                if is_correct:
                    correct_count += 1

                # Save response via backend
                try:
                    requests.post(
                        f"{BACKEND_URL}/quiz/response",
                        json={
                            "user_id": st.session_state["user_id"],
                            "quiz_id": quiz_id,
                            "question_index": i,
                            "chosen_index": int(chosen_index),
                            "is_correct": bool(is_correct),
                        },
                        timeout=60,
                    )
                except Exception as e:
                    st.error(f"Error calling backend /quiz/response: {e}")

            st.session_state["quiz_submitted"] = True
            st.success(f"You scored {correct_count} / {total}")

            # Optionally reveal correct answers
            with st.expander("Show Correct Answers & Explanations"):
                for i, mcq in enumerate(mcq_dicts):
                    st.markdown(f"**Q{i+1}. {mcq['question']}**")
                    st.write("Options:")
                    for idx, opt in enumerate(mcq["options"]):
                        prefix = "✅" if idx == mcq["correct_index"] else "  "
                        st.write(f"{prefix} {chr(65+idx)}. {opt}")
                    if mcq.get("explanation"):
                        st.write(f"_Explanation:_ {mcq['explanation']}")
                    st.markdown("---")


# ---------- COACH TAB ----------

with tab_coach:
    st.header("Learning Coach")

    if st.button("Compute Progress & Show Raw Stats", key="btn_compute_progress"):
        with st.spinner("Calling backend /coach/advice (for stats)..."):
            try:
                resp = requests.post(
                    f"{BACKEND_URL}/coach/advice",
                    json={"user_id": st.session_state["user_id"]},
                    timeout=120,
                )
                data = resp.json()
                stats = data.get("progress", {})
                st.markdown("### Progress Summary (Raw Data)")
                st.json(stats)
            except Exception as e:
                st.error(f"Error calling backend /coach/advice: {e}")

    if st.button("Get Coaching Advice", key="btn_get_coaching"):
        with st.spinner("Calling backend /coach/advice..."):
            try:
                resp = requests.post(
                    f"{BACKEND_URL}/coach/advice",
                    json={"user_id": st.session_state["user_id"]},
                    timeout=120,
                )
                data = resp.json()
                advice = data.get("advice", "")
                st.markdown("### Coaching Advice")
                st.write(advice)
            except Exception as e:
                st.error(f"Error calling backend /coach/advice: {e}")
