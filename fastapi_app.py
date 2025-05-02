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

# ───────────────────────────────────────────────────────────────
# OpenAI klient
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Welcome message
WELCOME_MSG = Path("prompts/welcome_message.md").read_text(
    encoding="utf-8"
) if Path("prompts/welcome_message.md").exists() else "**Welcome message nenalezen.**"

# Naivní per‑chat paměť („co jsem právě nabídl?“)
last_suggestion_memory: dict[str, str] = {}      # chat_id → "cv" | "meeting" | "github" | "portfolio"

# ───────────────────────────────────────────────────────────────
# Pydantic modely
class QueryRequest(BaseModel):
    question: str

class MeetingIntentRequest(BaseModel):
    message: str

class ChatMessage(BaseModel):
    chat_id: str
    message: str

# ───────────────────────────────────────────────────────────────
@app.get("/welcome")
async def get_welcome():
    """Statická uvítací zpráva"""
    return {"welcome": WELCOME_MSG}

# ───────────────────────────────────────────────────────────────
@app.post("/ask")
async def ask_question(request: QueryRequest):
    """RAG / FAQ dotaz (přímo, bez CTA logiky)"""
    try:
        answer = retrieve_answer(request.question)
        return {"answer": answer}
    except Exception as e:
        return {"error": str(e)}

# ───────────────────────────────────────────────────────────────
@app.post("/check_meeting_intent")
async def check_meeting_intent(request: MeetingIntentRequest):
    """
    Vrací YES / NO podle toho, zda text obsahuje návrh dne/času.
    (Původní funkčnost beze změn.)
    """
    print("➡️ Přišel request:", request.message)
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content":
                    "Jsi asistent, který odpovídá pouze YES nebo NO. "
                    "YES pokud zpráva obsahuje návrh dne nebo času schůzky. "
                    "NO pokud ne. Pokud si nejsi jistý, odpověz NO."
                 },
                {"role": "user", "content": request.message}
            ],
            temperature=0,
            max_tokens=5
        )
        intent = response.choices[0].message.content.strip().upper()
        print("🟢 OpenAI odpověď:", intent)
        return {"intent": intent}
    except Exception as e:
        print("❌ Chyba:", e)
        return {"error": str(e)}

# ───────────────────────────────────────────────────────────────
@app.post("/chat")
async def chat_handler(msg: ChatMessage):
    """
    Hlavní konverzační endpoint.
    Vrací: { "answer": "...", "action": "cv|meeting|plain" }
    - ukládá výzvy do paměti
    - reaguje na 'ano' / 'jo' podle uložené výzvy
    - jinak volá RAG jako fallback
    """
    user_input = msg.message.strip().lower()
    chat_id    = msg.chat_id

    # 1️⃣  Uživatel říká ANO / JO  ─────────────────────────────
    if user_input in {"ano", "jo", "jasně", "souhlasím"}:
        last = last_suggestion_memory.get(chat_id)

        if last == "cv":
            return {"answer": "Posílám životopis. 📄", "action": "cv"}
        if last == "meeting":
            return {"answer": "Nabízím tyto volné termíny…", "action": "meeting"}
        if last == "github":
            return {"answer": "Tady je Martinův GitHub: https://github.com/Matty-Jaris",
                    "action": "plain"}
        if last == "portfolio":
            return {"answer": "Portfolio najdete na: https://portfolio-weather.onrender.com",
                    "action": "plain"}

        return {"answer": "Na co přesně reagujete? GitHub, CV nebo schůzku?",
                "action": "plain"}

    # 2️⃣  Dotaz vyvolávající výzvu (uložíme paměť) ────────────
    if any(w in user_input for w in {"cv", "životopis"}):
        last_suggestion_memory[chat_id] = "cv"
        return {"answer": "Mám vám poslat životopis?", "action": "plain"}

    if any(w in user_input for w in {"pohovor", "schůzka", "setkat"}):
        last_suggestion_memory[chat_id] = "meeting"
        return {"answer": "Mám nabídnout volné termíny na schůzku?", "action": "plain"}

    if "github" in user_input:
        last_suggestion_memory[chat_id] = "github"
        return {"answer": "Chcete vidět GitHub?", "action": "plain"}

    if "portfolio" in user_input:
        last_suggestion_memory[chat_id] = "portfolio"
        return {"answer": "Chcete vidět portfolio?", "action": "plain"}

    # 3️⃣  Fallback – RAG / FAQ  ───────────────────────────────
    try:
        answer = retrieve_answer(user_input)
        return {"answer": answer, "action": "plain"}
    except Exception as e:
        return {"answer": f"Došlo k chybě: {e}", "action": "plain"}

