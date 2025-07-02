from fastapi import FastAPI
from pydantic import BaseModel
import os
from pathlib import Path
from openai import OpenAI
from rag.query_from_pinecone import retrieve_answer
from datetime import datetime
import requests
from fastapi.responses import JSONResponse
import asyncio
from fastapi.responses import StreamingResponse
from fastapi import Body, BackgroundTasks
import re, time, httpx, json
from typing import Optional


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

import time
import httpx
from fastapi import BackgroundTasks

@app.post("/ask_stream")
async def ask_stream(request: StreamedQuestionRequest, background_tasks: BackgroundTasks):
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_API_TOKEN")
    TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText"
    import re                                       # přidej na začátek souboru

    def stream_sync(answer_text, chat_id, message_id):
        answer_text = answer_text.replace("\\n", "\n")          # escapované → reálné
        tokens = re.findall(r'\n|[^\s]+', answer_text)          # ← hlavní změna

        response_text = ""
        with httpx.Client(timeout=10.0) as client_http:
            for tok in tokens:
                response_text += "\n" if tok == "\n" else f"{tok} "
                client_http.post(
                    TELEGRAM_API,
                    json={
                        "chat_id":    chat_id,
                        "message_id": message_id,
                        "text":       response_text.rstrip()
                    }
                )
                time.sleep(0.1)

    # def stream_sync(answer_text, chat_id, message_id):
    #     words = answer_text.split()
    #     response_text = ""
    #     with httpx.Client(timeout=10.0) as client_http:  # ← Nastavený vyšší timeout!
    #         for word in words:
    #             response_text += word + " "
    #             client_http.post(TELEGRAM_API, json={
    #                 "chat_id": chat_id,
    #                 "message_id": message_id,
    #                 "text": response_text.strip()
    #             })
    #             time.sleep(0.1)  # O něco delší pauza mezi requesty (0.1 sec)

    faq_answer = retrieve_answer(request.question)

    if faq_answer and len(faq_answer.strip()) > 10:
        final_answer = faq_answer
    else:
        final_answer = "Omlouvám se, zatím k této otázce nemám odpověď ve FAQ."

    background_tasks.add_task(
        stream_sync,
        final_answer,
        request.chat_id,
        request.message_id
    )

    return {"success": True}


@app.post("/say_stream")
async def say_stream(
    chat_id: str = Body(...),
    message_id: int = Body(...),
    text: str = Body(...),
    reply_markup: Optional[dict] = Body(None),          # ← ① NOVÉ pole (může být None)
    background_tasks: BackgroundTasks = None
):
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_API_TOKEN")
    TELEGRAM_API   = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText"

    def stream_prepared(text, chat_id, message_id, reply_markup):
        text = text.replace("\\n", "\n")
        tokens = re.findall(r'\n|[^\s]+', text)

        resp = ""
        with httpx.Client(timeout=10) as http:
            for tok in tokens:
                resp += "\n" if tok == "\n" else f"{tok} "
                http.post(
                    TELEGRAM_API,
                    json={
                        "chat_id":    chat_id,
                        "message_id": message_id,
                        "text":       resp.rstrip(),
                         "parse_mode": "HTML"
                    }
                )
                time.sleep(0.1)

            # ▶️ KO NE C  – po dopsání pošli ještě jednou celé tělo + tlačítka
            if reply_markup:
                http.post(
                    TELEGRAM_API,
                    json={
                        "chat_id":    chat_id,
                        "message_id": message_id,
                        "text":       resp.rstrip(),
                        "reply_markup": reply_markup,
                        "parse_mode": "HTML"
                    }
                )

    background_tasks.add_task(
        stream_prepared, text, chat_id, message_id, reply_markup
    )
    return {"success": True}


