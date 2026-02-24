import google.generativeai as genai 

api_key="AIzaSyCVAHr3SHrgYVk34hfV9EIdKedCaYbiM1A"
MODEL =  "gemini-3-flash-preview"

SYSTEM_PROMPT = "Casual chatbot"

def setup():
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name=MODEL, system_instruction=SYSTEM_PROMPT)
    chat = model.start_chat(history=[])
    return chat

chat = setup()
response = chat.send_message("hello how are you", stream=False)
print(response)