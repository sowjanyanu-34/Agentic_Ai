import google.generativeai as genai
api_key="AIzaSyCVAHr3SHrgYVk34hfV9EIdKedCaYbiM1A"
MODEL =  "gemini-3-flash-preview"

SYSTEM_PROMPT = """
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

Ensure the recipe is beginner-friendly."""

def setup():
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name=MODEL, system_instruction=SYSTEM_PROMPT)
    chat = model.start_chat(history=[])
    return chat
def ask_ai_stream(chat, message:str)->str:
    response = chat.send_message(message, stream=True)
    full_reply=""
    for chunk in response:
        print(chunk.text,end="",flush=True)
        full_reply+=chunk.text
    print("\n")
    return full_reply
chat = setup()
while True:
    user_input=input("you:").strip()
    ask_ai_stream(chat,user_input)