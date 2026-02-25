import streamlit as st
import ollama
import time
MODEL="phi3:mini"
SYSTEM_PROMPT = """
ROLE:Act as a Desi cooking assistant. You will provide recipes based on the dish name provided by the user. The recipes should be authentic and reflect traditional Indian cooking styles.
Input:
Dish name
Output:
A well-structured recipe with ingredients, measurements, step-by-step instructions, cooking time, and serving size.
as an json format no markdown
Instructions:

Use simple and clear language.
Include exact quantities.
Provide step-by-step cooking instructions.
Mention preparation time and cooking time.
Ensure the recipe is beginner-friendly.
"""

def ask_ai_stream(message:str)->str:
    response = ollama.chat(
        model=MODEL,
        messages=[{"role":"user","content":message}],
        options={"system": SYSTEM_PROMPT}
    )
    return response["message"]["content"]

# MUST be first streamlit command
st.set_page_config(
    page_title="First Chatbot",
    page_icon=":)",
    layout="centered"
)

st.header("Ollama")

# ✅ prevent reset
if "messages" not in st.session_state:
    st.session_state.messages = []

if "bot_name" not in st.session_state:
    st.session_state.bot_name ="Jarvis"

with st.sidebar:
    st.title("Chatbot Settings")
    st.session_state.bot_name = st.text_input(
        "Bot Name", value=st.session_state.bot_name
        )

st.header("Welcome to day 2 of RAG Chatbot")
st.divider()

# Conversation history
for msg in st.session_state.messages:
    role = msg['role']
    content = msg['content']
    with st.chat_message(role):
        st.markdown(content)

user_input = st.text_input("Your prompt to chatbot")

if user_input:
    st.session_state.messages.append({
        "role": "user",
        "content": user_input,
        "timestamp": time.strftime("%H:%M:%S")
    })

    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Typing......"):
            time.sleep(0.8)

        response = ask_ai_stream(user_input)
        st.markdown(response)

    st.session_state.messages.append({
        "role": "assistant",
        "content": response
    })