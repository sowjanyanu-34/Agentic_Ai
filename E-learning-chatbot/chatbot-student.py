import streamlit as st
import ollama
import time

MODEL = "phi3:mini"

SYSTEM_PROMPT = """
You are a Student Learning Memory Assistant.

Your job is to help students learn by remembering:
- Subject preference
- Difficulty level (Easy / Medium / Hard)
- Weak topics

Rules:
1. Remember subject and difficulty during the session.
2. Add topics to weak topics if the student answers incorrectly.
3. Increase difficulty if the student performs well.
4. Decrease difficulty if the student struggles.
5. Adjust explanation based on difficulty:
   - Easy → Simple explanation
   - Medium → Detailed explanation
   - Hard → Deep explanation
6. If the user types "Reset session", clear all memory.
7. Keep answers clear and educational.
8. Do not show internal memory unless asked.
"""

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="Smart Learning Chatbot",
    page_icon="🤖",
    layout="centered"
)

# ---------------- SESSION STATE ----------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "bot_name" not in st.session_state:
    st.session_state.bot_name = "Jarvis"

if "difficulty" not in st.session_state:
    st.session_state.difficulty = "Easy"

if "score" not in st.session_state:
    st.session_state.score = 0


# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.title("⚙️ Chatbot Settings")

    st.session_state.bot_name = st.text_input(
        "Bot Name",
        value=st.session_state.bot_name
    )

    st.session_state.difficulty = st.selectbox(
        "Select Difficulty",
        ["Easy", "Medium", "Hard"],
        index=["Easy","Medium","Hard"].index(st.session_state.difficulty)
    )

    theme = st.radio("Theme", ["Light", "Dark"])

    if st.button("🗑 Clear Chat"):
        st.session_state.messages = []
        st.session_state.score = 0
        st.rerun()

    st.divider()
    st.subheader("📊 Performance")
    st.progress(st.session_state.score)


# ---------------- THEME STYLE ----------------
if theme == "Dark":
    st.markdown(
        """
        <style>
        .stApp {
            background-color: #0E1117;
            color: white;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

# ---------------- HEADER ----------------
st.title("🤖 Smart Learning Assistant")
st.caption("Interactive AI Tutor with Memory & Difficulty Control")
st.divider()

# ---------------- AI FUNCTION ----------------
def ask_ai_stream(message: str) -> str:
    response = ollama.chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Difficulty: {st.session_state.difficulty}\n\n{message}"}
        ]
    )
    return response["message"]["content"]


# ---------------- DISPLAY CHAT HISTORY ----------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="🤖" if msg["role"]=="assistant" else "👩"):
        st.markdown(msg["content"])
        if "timestamp" in msg:
            st.caption(msg["timestamp"])


# ---------------- USER INPUT ----------------
user_input = st.chat_input("Ask your question here...")

if user_input:

    # Save user message
    st.session_state.messages.append({
        "role": "user",
        "content": user_input,
        "timestamp": time.strftime("%H:%M:%S")
    })

    with st.chat_message("user", avatar="👩"):
        st.markdown(user_input)

    # AI Response
    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("Typing..."):
            time.sleep(0.5)
            response = ask_ai_stream(user_input)

        # Typing animation
        placeholder = st.empty()
        typed_text = ""

        for char in response:
            typed_text += char
            placeholder.markdown(typed_text)
            time.sleep(0.005)

    # Increase score slightly (demo logic)
    if len(user_input) > 5:
        st.session_state.score = min(100, st.session_state.score + 5)

    # Save assistant message
    st.session_state.messages.append({
        "role": "assistant",
        "content": response,
        "timestamp": time.strftime("%H:%M:%S")
    })