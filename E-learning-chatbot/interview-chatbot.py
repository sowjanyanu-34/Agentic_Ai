# =========================
# IMPORTS
# =========================
import os
import hashlib
import streamlit as st
import chromadb
import ollama
from pypdf import PdfReader
import json
import re

# =========================
# CONFIG
# =========================
CHROMA_PATH = "./chroma_db"
COLLECTION = "hireready_interview"

EMBED_MODEL = "nomic-embed-text"
CHAT_MODEL = "phi3:mini"

CHUNK_SIZE = 400
CHUNK_OVERLAP = 80
N_RESULTS = 5
DIST_CUTOFF = 0.8

# =========================
# CHROMA INITIALIZATION
# =========================
@st.cache_resource
def get_collection():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    return client.get_or_create_collection(
        name=COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )

# =========================
# HELPER FUNCTIONS
# =========================
def chunk_text(text: str) -> list[str]:
    chunks = []
    start = 0
    text_length = len(text)
    while start < text_length:
        end = min(start + CHUNK_SIZE, text_length)
        if end < text_length:
            for boundary in ("\n\n", "\n", ". ", " "):
                pos = text.rfind(boundary, start, end)
                if pos != -1 and pos > start:
                    end = pos + len(boundary)
                    break
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= text_length:
            break
        next_start = end - CHUNK_OVERLAP
        start = next_start if next_start > start else end
    return chunks

def read_file(uploaded_file) -> str:
    if uploaded_file.name.endswith(".pdf"):
        reader = PdfReader(uploaded_file)
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)
    return uploaded_file.read().decode("utf-8", errors="ignore")

def embed(texts: list[str]) -> list[list[float]]:
    response = ollama.embed(model=EMBED_MODEL, input=texts)
    return response["embeddings"]

def make_id(source: str, idx: int) -> str:
    return f"{hashlib.md5(source.encode()).hexdigest()[:8]}_{idx}"

# =========================
# INGEST KNOWLEDGE BASE
# =========================
def ingest(uploaded_file, collection, metadata: dict) -> int:
    name = uploaded_file.name
    text = read_file(uploaded_file)
    if not text.strip():
        return 0
    chunks = chunk_text(text)
    BATCH = 16
    for i in range(0, len(chunks), BATCH):
        batch = chunks[i:i + BATCH]
        collection.upsert(
            documents=batch,
            embeddings=embed(batch),
            metadatas=[{"source": name, "chunk": i + j, **metadata} for j in range(len(batch))],
            ids=[make_id(name, i + j) for j in range(len(batch))],
        )
    return len(chunks)

# =========================
# RETRIEVAL
# =========================
def retrieve(query: str, collection, company: str, round_type: str, role: str) -> list[dict]:
    if collection.count() == 0:
        return []
    query_vec = embed([query])[0]
    results = collection.query(
        query_embeddings=[query_vec],
        n_results=min(N_RESULTS, collection.count()),
        include=["documents", "metadatas", "distances"],
    )
    output = []
    for doc, meta, dist in zip(results["documents"][0], results["metadatas"][0], results["distances"][0]):
        if dist < DIST_CUTOFF and meta.get("company") == company and meta.get("round_type") == round_type and meta.get("role") == role:
            output.append({"text": doc, "source": meta.get("source"), "distance": round(dist, 4)})
    return output

# =========================
# BUILD INTERVIEW PROMPT
# =========================
def build_interview_prompt(conversation_history: list[dict], question_chunks: list[dict], eval_chunks: list[dict], round_type: str) -> str:
    context = "\n\n".join(f"[SOURCE: {c['source']}]\n{c['text']}" for c in question_chunks)
    eval_context = "\n\n".join(f"[SOURCE: {c['source']}]\n{c['text']}" for c in eval_chunks)
    history = "\n".join(f"Student: {m['user']}\nInterviewer: {m['bot']}" for m in conversation_history)
    return f"""
You are HireReady, a professional {round_type} interviewer.

Your job:
- Ask realistic interview questions from the retrieved context below.
- Evaluate the student's answers against retrieved evaluation rubrics.
- Do NOT give hints or confirm correctness during the interview.
- Maintain professional and consistent interviewer persona.

CONTEXT — Questions:
{context}

CONTEXT — Evaluation Rubrics:
{eval_context}

CONVERSATION HISTORY:
{history}

INSTRUCTIONS:
1. Generate the next question if interview is ongoing.
2. If the interview should end, indicate and switch to feedback mode.
3. Evaluate answers based on retrieved rubrics ONLY.

Output only in JSON:
{{
  "next_question": "<Question or null if interview over>",
  "feedback": "<Feedback for last answer or empty if none>"
}}
"""

# =========================
# ROBUST JSON PARSER
# =========================
def parse_json_response(text: str) -> dict:
    try:
        return json.loads(text)
    except:
        # Extract JSON object from text
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except:
                return {}
        return {}

# =========================
# STREAMLIT UI
# =========================
st.set_page_config(page_title="HireReady", layout="centered")
st.title("HireReady — Mock Placement Interview Chatbot")

collection = get_collection()

# -------------------------
# SIDEBAR — ONLY FILE UPLOAD
# -------------------------
with st.sidebar:
    st.header("Upload Knowledge Base (TXT/PDF)")
    uploaded_files = st.file_uploader("Upload Files", type=["txt", "pdf"], accept_multiple_files=True)

# -------------------------
# MAIN PANEL — METADATA + INTERVIEW
# -------------------------
st.header("Start Mock Interview")

# Metadata input
selected_company = st.text_input("Company Name", value="google")
selected_role = st.text_input("Role / Position", value="Software Engineer")
selected_round = st.selectbox("Round", ["HR", "Technical"])
difficulty_level = st.selectbox("Difficulty Level", ["Easy", "Medium", "Hard"])

# Upload files using center metadata
if uploaded_files:
    st.markdown(f"**Files ready to upload:** {', '.join([f.name for f in uploaded_files])}")
    if st.button("Add to Knowledge Base (Use Center Metadata)"):
        metadata = {
            "company": selected_company.strip(),
            "role": selected_role.strip(),
            "round_type": selected_round,
            "difficulty": difficulty_level
        }
        for file in uploaded_files:
            with st.spinner(f"Ingesting {file.name}..."):
                n = ingest(file, collection, metadata)
            st.success(f"{file.name} → {n} chunks added")

# Initialize conversation
if "conversation" not in st.session_state:
    st.session_state.conversation = []
if "interview_over" not in st.session_state:
    st.session_state.interview_over = False

answer = st.text_area("Your Answer:", height=150)

if st.button("Submit Answer") and not st.session_state.interview_over:
    query_text = "Technical Question" if selected_round == "Technical" else "HR Question"
    eval_query = "evaluation rubric"

    question_chunks = retrieve(query_text, collection, selected_company, selected_round, selected_role)
    eval_chunks = retrieve(eval_query, collection, selected_company, selected_round, selected_role)

    prompt = build_interview_prompt(st.session_state.conversation, question_chunks, eval_chunks, selected_round)

    response = ollama.chat(
        model=CHAT_MODEL,
        messages=[{"role": "system", "content": "You are HireReady."}, {"role": "user", "content": prompt}],
    )

    output = parse_json_response(response["message"]["content"])
    feedback = output.get("feedback", "")
    next_q = output.get("next_question", "")

    st.session_state.conversation.append({"user": answer, "bot": feedback})
    st.markdown(f"**Feedback:** {feedback}")

    if next_q:
        st.markdown(f"**Next Question:** {next_q}")
    else:
        st.session_state.interview_over = True
        st.markdown("**Interview Over! Generating Scorecard...**")
        score_prompt = f"""
Conversation:
{st.session_state.conversation}

Generate a structured scorecard with:
- Communication (1-10)
- Technical Accuracy (1-10)
- Confidence (1-10)
- Company-Culture Fit (1-10)
Provide brief reasoning for each score.
"""
        score_response = ollama.chat(
            model=CHAT_MODEL,
            messages=[{"role": "system", "content": "You are HireReady scoring interviewer."}, {"role": "user", "content": score_prompt}],
        )
        st.markdown("**Scorecard:**")
        st.markdown(score_response["message"]["content"])