from fastapi import FastAPI
from pydantic import BaseModel
import os
from pathlib import Path
from openai import OpenAI
from rag.query_from_pinecone import retrieve_answer
from datetime import datetime
import requests
from fastapi.responses import JSONResponse
from rag.query_from_pinecone import retrieve_answer





app = FastAPI()

# OpenAI klient (správně pro novou verzi knihovny)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

WELCOME_PATH = Path("prompts/welcome_message.md")
if WELCOME_PATH.exists():
    WELCOME_MSG = WELCOME_PATH.read_text(encoding="utf-8")
else:
    WELCOME_MSG = "**Welcome message nenalezen.**"

class QueryRequest(BaseModel):
    question: str

class MeetingIntentRequest(BaseModel):
    message: str

class ContactInfoRequest(BaseModel):
    message: str

class StreamedQuestionRequest(BaseModel):
    question: str
    chat_id: str
    message_id: int




@app.get("/welcome")
async def get_welcome():
    """
    Vrátí statickou uvítací zprávu pro první kontakt s uživatelem.
    Žádné parametry nepotřebuje – logiku 'poslat jen jednou'
    řeší volající (např. handler /start v Telegram bota).
    """
    return {"welcome": WELCOME_MSG}



@app.post("/ask")
async def ask_question(request: QueryRequest):
    try:
        answer = retrieve_answer(request.question)
        return {"answer": answer}
    except Exception as e:
        return {"error": str(e)}



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


from datetime import datetime

@app.post("/extract_date_time")
async def extract_date_time(request: MeetingIntentRequest):
    print("➡️ Zpráva od n8n:", request.message)  # Debug log
    try:
        today = datetime.today()
        current_year = today.year

        prompt = (
            "Tvým úkolem je rozpoznat termín schůzky ze zadané zprávy uživatele. "
            "Pokud najdeš datum a čas, vrať výstup ve formátu DD.MM.YYYY HH:mm. "
            f"Pokud není uveden rok, doplň aktuální ({current_year}). "
            "Pokud je uveden jen den v týdnu (např. 'středa') a datum (např. '21.5.'), a čas (např. '17:00'), zformátuj výstup. "
            "Příklady:\n"
            "- 'středa 21.5. v 17:00' → 21.05.2024 17:00\n"
            "- 'čtvrtek 6.6.2024 v 9 hodin' → 06.06.2024 09:00\n"
            "- 'v pátek odpoledne' → NEPLATNÉ\n"
            "- 'zítra v 14:00' → NEPLATNÉ\n"
            "Pokud není termín dostatečně konkrétní, odpověz přesně NEPLATNÉ."
        )

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": request.message}
            ],
            temperature=0,
            max_tokens=30
        )

        extracted_term = response.choices[0].message.content.strip()
        print("🟢 Rozpoznaný termín:", extracted_term)

        if extracted_term.upper() == "NEPLATNÉ":
            return {"success": False, "term": None, "message": "Datum a čas nebyly rozpoznány."}

        return {"success": True, "term": extracted_term, "message": "Datum a čas úspěšně rozpoznány."}

    except Exception as e:
        print("❌ Chyba při extrakci termínu:", e)
        return {"success": False, "term": None, "error": str(e)}


@app.post("/parse_contact_info")
async def parse_contact_info(request: ContactInfoRequest):
    print("➡️ Parsing kontaktu:", request.message)
    try:
        prompt = (
            "Z následující zprávy extrahuj jméno, telefonní číslo a e-mail. "
            "Výstup vrať přesně ve formátu JSON:\n"
            "{\"name\": \"...\", \"phone\": \"...\", \"email\": \"...\"}\n\n"
            f"Zpráva: {request.message}"
        )

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=150
        )

        content = response.choices[0].message.content.strip()

        print("🟢 Výstup OpenAI:\n", content)

        # Pokus o převod na dict (bezpečnější verze)
        import json
        import re
        json_string = re.sub(r"```(?:json)?\n?|```", "", content.strip())
        result = json.loads(json_string)

        return {
            "success": True,
            "name": result.get("name"),
            "phone": result.get("phone"),
            "email": result.get("email")
        }

    except Exception as e:
        print("❌ Chyba při parsování kontaktu:", e)
        return {"success": False, "error": str(e)}

from rag.query_from_pinecone import retrieve_answer  # přidej nahoru k ostatním

@app.post("/ask_stream")
async def ask_stream(request: StreamedQuestionRequest):
    try:
        # ⬅️ Získání kontextu z FAQ (RAG)
        faq_context = retrieve_answer(request.question)
        if not faq_context:
            faq_context = ""  # Fallback pro případ None

        # 🔁 Příprava streamovaného požadavku na OpenAI
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": faq_context},
                {"role": "user", "content": request.question}
            ],
            stream=True
        )

        # 📬 Telegram API
        TELEGRAM_TOKEN = os.getenv("TELEGRAM_API_TOKEN")
        TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText"

        full_message = ""
        previous = ""
        import time
        last_sent = time.time()

        for chunk in response:
            if hasattr(chunk.choices[0].delta, "content"):
                delta = chunk.choices[0].delta.content
                full_message += delta

                # 🛡 Přeskakuj stejné nebo příliš časté zprávy
                if full_message.strip() == previous.strip():
                    continue
                if time.time() - last_sent < 0.15:
                    continue

                previous = full_message
                last_sent = time.time()

                print("🧩 Sending:", full_message)

                res = requests.post(TELEGRAM_API, data={
                    "chat_id": request.chat_id,
                    "message_id": request.message_id,
                    "text": full_message
                })

                print("📨 Telegram:", res.status_code, res.text)

        return JSONResponse(content={"success": True})

    except Exception as e:
        print("❌ Chyba ve streamu:", e)
        return {"success": False, "error": str(e)}

from fastapi import Body

@app.post("/say_stream")
async def say_stream(
    chat_id: str = Body(...),
    message_id: int = Body(...),
    text: str = Body(...)
):
    try:
        # Telegram API setup
        TELEGRAM_TOKEN = os.getenv("TELEGRAM_API_TOKEN")
        TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText"

        full_message = ""
        previous = ""
        import time
        last_sent = time.time()

        # Rozsekání textu po slovech (můžeš změnit na znaky)
        chunks = text.split(" ")

        for chunk in chunks:
            full_message += chunk + " "

            if full_message.strip() == previous.strip():
                continue
            if time.time() - last_sent < 0.12:
                continue

            previous = full_message
            last_sent = time.time()

            print("🧩 Sending:", full_message)

            res = requests.post(TELEGRAM_API, data={
                "chat_id": chat_id,
                "message_id": message_id,
                "text": full_message.strip()
            })

            print("📨 Telegram:", res.status_code, res.text)

        return JSONResponse(content={"success": True})

    except Exception as e:
        print("❌ Chyba ve streamu:", e)
        return {"success": False, "error": str(e)})



