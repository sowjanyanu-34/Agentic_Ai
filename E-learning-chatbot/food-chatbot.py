import os
import streamlit as st
from google import genai
from google.genai import types


st.set_page_config(page_title="Agentic Food Chatbot", layout="centered")
st.title("🍽️ Agentic Food Bot - Bheemasena")

api_key = "AIzaSyBgewJ1zmPy7lJnqqi7OxnCAxPRrJHNtAw"
MODEL = "gemini-flash-latest"


TOOLS = types.Tool(function_declarations=[
    types.FunctionDeclaration(
        name="browse_menu",
        description="Browse the food menu by category or all items",
        parameters={
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["all", "desserts", "starters"],
                    "description": "Menu category"
                }
            },
            "required": ["category"]
        }
    ),
    types.FunctionDeclaration(
        name="add_to_cart",
        description="Add a menu item to the cart using its item ID",
        parameters={
            "type": "object",
            "properties": {
                "item_id": {"type": "string"},
                "qty": {"type": "number"}
            },
            "required": ["item_id", "qty"]
        }
    ),
    types.FunctionDeclaration(
        name="place_order",
        description="Place the final order and clear the cart",
        parameters={"type": "object", "properties": {}}
    )
])

SYSTEM_PROMPT = """
You are Food Chatbot and your name is "Bheemasena", a friendly restaurant ordering assistant.
Help users browse the menu, add items, view their cart, and place orders.
Always use tools to perform actions. Mention item IDs when listing menu items.
Be concise and friendly.
"""

MENU = {
    "starters": [
        {"id": "S1", "name": "Gobi Manchurian", "price": 100},
        {"id": "S2", "name": "Paneer Manchurian", "price": 200},
        {"id": "S3", "name": "Mushroom Manchurian", "price": 80}
    ],
    "desserts": [
        {"id": "DS1", "name": "Chocolate Fudge", "price": 300},
        {"id": "DS2", "name": "Death by Chocolate", "price": 200},
        {"id": "DS3", "name": "Ferrero Rocher Ice Cream", "price": 180}
    ]
}


if "gemini_history" not in st.session_state:
    st.session_state.gemini_history = []

if "cart" not in st.session_state:
    st.session_state.cart = []

if "order_history" not in st.session_state:
    st.session_state.order_history = []

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


def browse_menu(category="all"):
    if category == "all":
        return MENU
    return {category: MENU.get(category, [])}

def add_to_cart(item_id, qty=1):
    for cat_items in MENU.values():
        for item in cat_items:
            if item["id"].upper() == item_id.upper():
                for ci in st.session_state.cart:
                    if ci["id"] == item["id"]:
                        ci["qty"] += qty
                        return {"status": "updated item", "cart": st.session_state.cart}
                st.session_state.cart.append({**item, "qty": qty})
                return {"status": "added new item", "cart": st.session_state.cart}
    return {"status": "error", "message": "Item not found"}

def place_order():
    if not st.session_state.cart:
        return {"status": "error", "message": "Cart is empty"}

    total = sum(item["price"] * item["qty"] for item in st.session_state.cart)
    order_id = f"ORD-{len(st.session_state.order_history)+1}"

    st.session_state.order_history.append({
        "id": order_id,
        "items": st.session_state.cart.copy(),
        "total": total
    })

    st.session_state.cart = []
    return {"status": "success", "order_id": order_id, "total": total}


TOOL_MAP = {
    "browse_menu": lambda args: browse_menu(args.get("category", "all")),
    "add_to_cart": lambda args: add_to_cart(args.get("item_id"), int(args.get("qty", 1))),
    "place_order": lambda args: place_order()
}


prompt = st.text_input("Ask Bheemasena 🍲", placeholder="Show starters / Add S1 qty 2 / Place order")

if st.button("Ask") and prompt:
    client = genai.Client(api_key=api_key)

    # store user message
    st.session_state.gemini_history.append(
        types.Content(role="user", parts=[types.Part(text=prompt)])
    )

    with st.status("🤖 Thinking..."):
        response = client.models.generate_content(
            model=MODEL,
            contents=st.session_state.gemini_history,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=[TOOLS]
            )
        )

        candidate = response.candidates[0]

        # save model response to history
        st.session_state.gemini_history.append(
            types.Content(role="model", parts=candidate.content.parts)
        )

        # process each part
        for part in candidate.content.parts:
            if part.text:
                st.markdown(part.text)

            if part.function_call:
                tool_name = part.function_call.name
                tool_args = dict(part.function_call.args)

                st.write(f"🔧 Tool Call: {tool_name}")
                st.json(tool_args)

                if tool_name in TOOL_MAP:
                    result = TOOL_MAP[tool_name](tool_args)
                    st.success(result)
                else:
                    st.error(f"Unknown tool: {tool_name}")


st.subheader("🛒 Cart")
st.json(st.session_state.cart)

st.subheader("📦 Orders")
st.json(st.session_state.order_history)
api_key = "AIzaSyBgewJ1zmPy7lJnqqi7OxnCAxPRrJHNtAw"
