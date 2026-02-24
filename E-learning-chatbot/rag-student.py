# =========================
# IMPORTS
# =========================
import os
import hashlib
import streamlit as st
import chromadb
import ollama
from pypdf import PdfReader

# =========================
# CONFIG
# =========================
CHROMA_PATH = "./chroma_db"
COLLECTION = "docs"
EMBED_MODEL = "nomic-embed-text"
CHAT_MODEL = "phi3:mini"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
N_RESULTS = 5
DIST_CUTOFF = 0.7


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

        # ✅ FIXED: always advance forward, never go backwards
        next_start = end - CHUNK_OVERLAP
        start = next_start if next_start > start else end

    return chunks
def read_file(uploaded_file) -> str:
    if uploaded_file.name.endswith(".pdf"):
        reader = PdfReader(uploaded_file)
        return "\n\n".join(
            page.extract_text() or "" for page in reader.pages
        )
    return uploaded_file.read().decode("utf-8", errors="ignore")


def embed(texts: list[str]) -> list[list[float]]:
    response = ollama.embed(model=EMBED_MODEL, input=texts)
    return response["embeddings"]


def make_id(source: str, idx: int) -> str:
    return f"{hashlib.md5(source.encode()).hexdigest()[:8]}_{idx}"


def ingest(uploaded_file, collection) -> int:
    name = uploaded_file.name
    text = read_file(uploaded_file)

    if not text.strip():
        return 0

    print('chunking started')
    chunks = chunk_text(text)
    print('chunking ended')

    BATCH = 32
    for i in range(0, len(chunks), BATCH):
        batch = chunks[i:i + BATCH]

        collection.upsert(
            documents=batch,
            embeddings=embed(batch),
            metadatas=[
                {"source": name, "chunk": i + j}
                for j in range(len(batch))
            ],
            ids=[
                make_id(name, i + j)
                for j in range(len(batch))
            ],
        )

    return len(chunks)


def retrieve(query: str, collection) -> list[dict]:
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
        if dist < DIST_CUTOFF:
            output.append({
                "text": doc,
                "source": meta.get("source"),
                "distance": round(dist, 4),
            })

    return output


def build_prompt(query: str, chunks: list[dict]) -> str:
    if not chunks:
        return f"""
Answer the question.
If you don't know, say "I don't know".

QUESTION: {query}
ANSWER:
"""

    context = "\n\n".join(
        f"[{c['source']}]\n{c['text']}"
        for c in chunks
    )

    return f"""
Answer the question using ONLY the context below.
If the answer is not in the context, say "I don't know".

CONTEXT:
{context}

QUESTION:
{query}

ANSWER:
"""


# =========================
# STREAMLIT UI
# =========================
st.set_page_config(
    page_title="RAG Chatbot",
    layout="centered",
)

st.title("RAG in Action")

collection = get_collection()

# -------------------------
# SIDEBAR INGESTION
# -------------------------
with st.sidebar:
    st.header("Document Import")

    uploaded = st.file_uploader(
        "Upload Files",
        type=["txt", "pdf"],
        accept_multiple_files=True,
    )

    if uploaded and st.button("Add Knowledge", type="primary"):
        for file in uploaded:
            with st.spinner(f"Ingesting {file.name}..."):
                n = ingest(file, collection)
            st.success(f"{file.name} → {n} chunks added")

        #st.rerun()


# -------------------------
# CHAT STATE
# -------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


# -------------------------
# CHAT INPUT
# -------------------------
query = st.chat_input("Ask something about your data")

if query:
    st.session_state.messages.append({
        "role": "user",
        "content": query,
    })

    with st.chat_message("user"):
        st.markdown(query)

    chunks = retrieve(query, collection)
    prompt = build_prompt(query, chunks)

    with st.chat_message("assistant"):

        def stream_response():
            stream = ollama.chat(
                model=CHAT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                stream=True,
            )

            for chunk in stream:
                if "message" in chunk:
                    yield chunk["message"]["content"]

        answer = st.write_stream(stream_response())

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
    })