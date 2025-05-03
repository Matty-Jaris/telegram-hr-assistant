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
import os, re
from pathlib import Path
from openai import OpenAI
from rag.query_from_pinecone import retrieve_answer

app = FastAPI()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ── jednoduchá paměť CTA (chat_id -> "github" | "portfolio" | "leetcode") ──
last_suggestion_memory: dict[str, str] = {}

# ── welcome message ────────────────────────────────────────────────────────
WELCOME_MSG = Path("prompts/welcome_message.md").read_text(
    encoding="utf-8"
) if Path("prompts/welcome_message.md").exists() else "**Welcome message nenalezen.**"

# ── Pydantic modely ────────────────────────────────────────────────────────
class QueryRequest(BaseModel):
    question: str

class MeetingIntentRequest(BaseModel):
    message: str

class ChatMessage(BaseModel):
    chat_id: str
    message: str

# ── /welcome (beze změn) ───────────────────────────────────────────────────
@app.get("/welcome")
async def get_welcome():
    return {"welcome": WELCOME_MSG}

# ── /ask (beze změn) ───────────────────────────────────────────────────────
@app.post("/ask")
async def ask_question(req: QueryRequest):
    try:
        return {"answer": retrieve_answer(req.question)}
    except Exception as e:
        return {"error": str(e)}

# ── /check_meeting_intent (beze změn) ──────────────────────────────────────
@app.post("/check_meeting_intent")
async def check_meeting_intent(req: MeetingIntentRequest):
    try:
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system",
                 "content": "Jsi asistent, který vrací YES/NO podle toho, "
                            "zda text obsahuje návrh dne nebo času schůzky."},
                {"role": "user", "content": req.message}
            ],
            temperature=0, max_tokens=5
        )
        return {"intent": resp.choices[0].message.content.strip().upper()}
    except Exception as e:
        return {"error": str(e)}

# ── /chat – hlavní konverzace + CTA logika ─────────────────────────────────
@app.post("/chat")
async def chat_handler(msg: ChatMessage):
    chat_id    = msg.chat_id
    user_input = msg.message.strip().lower()

    # dávám krátké aliasy na klíčová slova
    KW_GH   = {"github", "repo", "projekty"}
    KW_PORT = {"portfolio"}
    KW_LC   = {"leetcode"}

    # 0) explicitní jednoslovné příkazy → rovnou odkaz ----------------
    if user_input in KW_GH:
        return {"answer": "Tady je GitHub: https://github.com/Matty-Jaris"}
    if user_input in KW_PORT:
        return {"answer": "Portfolio: https://portfolio-weather.onrender.com"}
    if user_input in KW_LC:
        return {"answer": "LeetCode řešení: https://github.com/Matty-Jaris/LeetCode-solutions"}

    # 1) odpověď typu "ano / jo" -------------------------------------
    if user_input in {"ano", "jo", "jasně", "souhlasím"}:
        last = last_suggestion_memory.get(chat_id)
        if last == "github":
            return {"answer": "Tady je GitHub: https://github.com/Matty-Jaris"}
        if last == "portfolio":
            return {"answer": "Portfolio: https://portfolio-weather.onrender.com"}
        if last == "leetcode":
            return {"answer": "LeetCode řešení: https://github.com/Matty-Jaris/LeetCode-solutions"}
        # nic uloženého
        return {"answer": "Na co přesně reagujete? GitHub, portfolio nebo LeetCode?"}

    # 2) dotaz obsahuje klíčová slova → uložíme CTA předem ------------
    if any(kw in user_input for kw in KW_GH):
        last_suggestion_memory[chat_id] = "github"
    elif any(kw in user_input for kw in KW_PORT):
        last_suggestion_memory[chat_id] = "portfolio"
    elif any(kw in user_input for kw in KW_LC):
        last_suggestion_memory[chat_id] = "leetcode"

    # 3) FAQ / RAG ----------------------------------------------------
    try:
        answer = retrieve_answer(user_input)
    except Exception as e:
        return {"answer": f"Došlo k chybě: {e}"}

    # 3a) pokud RAG nevrátil CTA, připojíme ji dynamicky --------------
    if last_suggestion_memory.get(chat_id) == "github" and "github" not in answer.lower():
        answer += " Chcete vidět GitHub?"
    elif last_suggestion_memory.get(chat_id) == "portfolio" and "portfolio" not in answer.lower():
        answer += " Chcete vidět portfolio?"
    elif last_suggestion_memory.get(chat_id) == "leetcode" and "leetcode" not in answer.lower():
        answer += " Chcete vidět příklad z LeetCode?"

    return {"answer": answer}



