# ==========================================================
# CodeSensei — AI Code Review Mentor
# ==========================================================

# =========================
# IMPORTS
# =========================
import hashlib
import streamlit as st
import chromadb
import ollama
from pypdf import PdfReader


# =========================
# CONFIG
# =========================
CHROMA_PATH = "./chroma_db"
COLLECTION = "code_standards"

EMBED_MODEL = "nomic-embed-text"
CHAT_MODEL = "phi3:mini"

CHUNK_SIZE = 300
CHUNK_OVERLAP = 50

N_RESULTS = 5
DIST_CUTOFF = 0.75


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
# TEXT CHUNKING
# =========================
def chunk_text(text: str):
    chunks = []
    start = 0

    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))

        if end < len(text):
            for boundary in ("\n\n", "\n", ". ", " "):
                pos = text.rfind(boundary, start, end)
                if pos != -1 and pos > start:
                    end = pos + len(boundary)
                    break

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = max(end - CHUNK_OVERLAP, end)

    return chunks


# =========================
# FILE READER
# =========================
def read_file(uploaded_file):
    if uploaded_file.name.endswith(".pdf"):
        reader = PdfReader(uploaded_file)
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)

    return uploaded_file.read().decode("utf-8", errors="ignore")


# =========================
# EMBEDDING
# =========================
def embed(texts):
    response = ollama.embed(model=EMBED_MODEL, input=texts)
    return response["embeddings"]


def make_id(source, idx):
    return f"{hashlib.md5(source.encode()).hexdigest()[:8]}_{idx}"


# =========================
# INGEST DOCUMENTS
# =========================
def ingest(uploaded_file, collection, language):
    text = read_file(uploaded_file)

    if not text.strip():
        return 0

    chunks = chunk_text(text)

    for i in range(0, len(chunks), 32):
        batch = chunks[i:i + 32]

        collection.upsert(
            documents=batch,
            embeddings=embed(batch),
            metadatas=[
                {
                    "source": uploaded_file.name,
                    "chunk_id": i + j,
                    "language": language,
                }
                for j in range(len(batch))
            ],
            ids=[make_id(uploaded_file.name, i + j) for j in range(len(batch))]
        )

    return len(chunks)


# =========================
# RETRIEVAL
# =========================
def retrieve(query, collection, language):
    if collection.count() == 0:
        return []

    query_vec = embed([query])[0]

    results = collection.query(
        query_embeddings=[query_vec],
        n_results=min(N_RESULTS, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    output = []

    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        if dist < DIST_CUTOFF and meta.get("language") == language:
            output.append({
                "text": doc,
                "source": meta.get("source", "Unknown"),
                "chunk_id": meta.get("chunk_id", "N/A"),
            })

    return output


# =========================
# MULTI-ASPECT RETRIEVAL
# =========================
def multi_aspect_retrieve(code, language, collection):
    aspects = [
        "naming conventions",
        "formatting rules",
        "function design",
        "comments and documentation",
        "error handling",
        "imports",
    ]

    all_chunks = []

    for aspect in aspects:
        query = f"{aspect} in {language} coding standards"
        all_chunks.extend(retrieve(query, collection, language))

    # remove duplicates
    unique = {}
    for chunk in all_chunks:
        unique[chunk["text"]] = chunk

    return list(unique.values())


# =========================
# PROMPT BUILDER
# =========================
def build_review_prompt(code, language, chunks):

    if not chunks:
        return """
VERDICT: No applicable standards found.
ISSUES: None
POSITIVES: None
"""

    context = "\n\n".join(
        f"[RULE_ID: {i+1} | SOURCE: {c['source']}]\n{c['text']}"
        for i, c in enumerate(chunks)
    )

    return f"""
You are CodeSensei, a strict senior code reviewer.

Review ONLY coding standards compliance.
Do NOT evaluate logic correctness.
Every issue MUST cite RULE_ID.

FORMAT:

VERDICT: <Good / Needs Improvement>

ISSUES:
- [Severity: ]
  Description:
  Violated Rule: RULE_ID

POSITIVES:
- Description
  Supported Rule: RULE_ID

=====================
CODING STANDARDS:
{context}

=====================
CODE:
{code}
"""


# =========================
# STREAMLIT UI
# =========================
st.set_page_config(page_title="AI reviewer", layout="centered")
st.title("AI Code Review Mentor")

collection = get_collection()

# ---------- Upload Standards ----------
with st.sidebar:
    st.header("Upload Coding Standards")

    std_language = st.selectbox(
        "Language",
        ["Python", "Java", "C++", "JavaScript"]
    )

    uploaded = st.file_uploader(
        "Upload Standards Files",
        type=["txt", "pdf"],
        accept_multiple_files=True,
    )

    if uploaded and st.button("Add to Knowledge Base"):
        for file in uploaded:
            with st.spinner(f"Ingesting {file.name}..."):
                n = ingest(file, collection, std_language)
            st.success(f"{file.name} → {n} chunks added")


# ---------- Code Review ----------
st.header("Submit Code for Review")

language = st.selectbox(
    "Select Programming Language",
    ["Python", "Java", "C++", "JavaScript"]
)

code_input = st.text_area("Paste your code here", height=300)

if st.button("Review Code"):

    if not code_input.strip():
        st.warning("Please paste code.")
        st.stop()

    if collection.count() == 0:
        st.error("No standards uploaded.")
        st.stop()

    with st.spinner("Reviewing..."):
        chunks = multi_aspect_retrieve(code_input, language, collection)
        prompt = build_review_prompt(code_input, language, chunks)

        response = ollama.chat(
            model=CHAT_MODEL,
            messages=[
                {"role": "user", "content": prompt}
            ],
        )

        st.markdown(response["message"]["content"])