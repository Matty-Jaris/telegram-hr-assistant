# from fastapi import FastAPI
# from pydantic import BaseModel
# import os
# from pathlib import Path
# from openai import OpenAI
# from rag.query_from_pinecone import retrieve_answer


# app = FastAPI()

# # OpenAI klient (správně pro novou verzi knihovny)
# client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# WELCOME_PATH = Path("prompts/welcome_message.md")
# if WELCOME_PATH.exists():
#     WELCOME_MSG = WELCOME_PATH.read_text(encoding="utf-8")
# else:
#     WELCOME_MSG = "**Welcome message nenalezen.**"

# class QueryRequest(BaseModel):
#     question: str

# class MeetingIntentRequest(BaseModel):
#     message: str



# @app.get("/welcome")
# async def get_welcome():
#     """
#     Vrátí statickou uvítací zprávu pro první kontakt s uživatelem.
#     Žádné parametry nepotřebuje – logiku 'poslat jen jednou'
#     řeší volající (např. handler /start v Telegram bota).
#     """
#     return {"welcome": WELCOME_MSG}



# @app.post("/ask")
# async def ask_question(request: QueryRequest):
#     try:
#         answer = retrieve_answer(request.question)
#         return {"answer": answer}
#     except Exception as e:
#         return {"error": str(e)}



# @app.post("/check_meeting_intent")
# async def check_meeting_intent(request: MeetingIntentRequest):
#     print("➡️ Přišel request:", request.message)  # Debug log
#     try:
#         response = client.chat.completions.create(
#             model="gpt-4o",
#             messages=[
#                 {"role": "system", "content": (
#                     "Jsi asistent, který odpovídá pouze YES nebo NO. "
#                     "YES pokud zpráva obsahuje návrh dne nebo času schůzky "
#                     "(např. 'Středa v 17:00', 'Úterý dopoledne'). "
#                     "NO pokud ne. Pokud si nejsi jistý, odpověz NO."
#                 )},
#                 {"role": "user", "content": request.message}
#             ],
#             temperature=0,
#             max_tokens=5
#         )
#         intent = response.choices[0].message.content.strip().upper()
#         print("🟢 OpenAI odpověď:", intent)  # Debug log
#         return {"intent": intent}
#     except Exception as e:
#         print("❌ Chyba:", e)  # Debug log
#         return {"error": str(e)}

from fastapi import FastAPI
from pydantic import BaseModel
import os
from pathlib import Path
from openai import OpenAI
from rag.query_from_pinecone import retrieve_answer

app = FastAPI()

# OpenAI klient (správně pro novou verzi knihovny)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Paměť poslední výzvy (naivní per-chat slovník)
last_suggestion_memory = {}

# Welcome message
WELCOME_PATH = Path("prompts/welcome_message.md")
if WELCOME_PATH.exists():
    WELCOME_MSG = WELCOME_PATH.read_text(encoding="utf-8")
else:
    WELCOME_MSG = "**Welcome message nenalezen.**"

# Příchozí dotazy
class QueryRequest(BaseModel):
    question: str

class MeetingIntentRequest(BaseModel):
    message: str

class ChatMessage(BaseModel):
    chat_id: str
    message: str

# 🔹 Welcome endpoint
@app.get("/welcome")
async def get_welcome():
    """
    Vrátí statickou uvítací zprávu pro první kontakt s uživatelem.
    """
    return {"welcome": WELCOME_MSG}

# 🔹 RAG dotaz
@app.post("/ask")
async def ask_question(request: QueryRequest):
    try:
        answer = retrieve_answer(request.question)
        return {"answer": answer}
    except Exception as e:
        return {"error": str(e)}

# 🔹 Detekce návrhu termínu
@app.post("/check_meeting_intent")
async def check_meeting_intent(request: MeetingIntentRequest):
    print("➡️ Přišel request:", request.message)  # Debug log
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": (
                    "Jsi asistent, který odpovídá pouze YES nebo NO. "
                    "YES pokud zpráva obsahuje návrh dne nebo času schůzky "
                    "(např. 'Středa v 17:00', 'Úterý dopoledne'). "
                    "NO pokud ne. Pokud si nejsi jistý, odpověz NO."
                )},
                {"role": "user", "content": request.message}
            ],
            temperature=0,
            max_tokens=5
        )
        intent = response.choices[0].message.content.strip().upper()
        print("🟢 OpenAI odpověď:", intent)  # Debug log
        return {"intent": intent}
    except Exception as e:
        print("❌ Chyba:", e)  # Debug log
        return {"error": str(e)}

# 🔹 Konverzační endpoint s pamětí poslední výzvy
@app.post("/chat")
async def chat_handler(msg: ChatMessage):
    user_input = msg.message.strip().lower()
    chat_id = msg.chat_id

    if user_input in ["ano", "jo", "jasně", "souhlasím"]:
        last = last_suggestion_memory.get(chat_id)

        if last == "github":
            return {"reply": "Tady je Martinův GitHub: https://github.com/matty-jaris"}
        elif last == "cv":
            return {"reply": "Tady je Martinovo CV: https://example.com/cv.pdf"}
        elif last == "portfolio":
            return {"reply": "Portfolio najdete na: https://portfolio-martin.onrender.com"}
        else:
            return {"reply": "Na co přesně reagujete? GitHub, CV nebo portfolio?"}

    # Uložení výzvy
    if "chcete vidět github" in user_input:
        last_suggestion_memory[chat_id] = "github"
        return {"reply": "Chcete vidět GitHub? 🙂"}

    elif "chcete vidět cv" in user_input or "životopis" in user_input:
        last_suggestion_memory[chat_id] = "cv"
        return {"reply": "Mám vám poslat Martinovo CV?"}

    elif "chcete vidět portfolio" in user_input:
        last_suggestion_memory[chat_id] = "portfolio"
        return {"reply": "Chcete vidět Martinovo portfolio?"}

    # Jinak použij RAG
    try:
        answer = retrieve_answer(user_input)
        return {"reply": answer}
    except Exception as e:
        return {"reply": f"Došlo k chybě: {str(e)}"}
