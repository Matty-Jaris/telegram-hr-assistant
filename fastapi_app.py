from fastapi import FastAPI, Body
from pydantic import BaseModel
from helpers import detect_intent, extract_datetime, parse_contact, get_faq_answer, log_to_airtable
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

app = FastAPI()
session_state = {}  # Na produkci raději Redis!

class ChatRequest(BaseModel):
    message: str
    session_id: str

@app.post("/chat")
async def chat_handler(req: ChatRequest):
    msg = req.message.strip()
    sid = req.session_id
    state = session_state.get(sid, {})

    # Už dojednáváme schůzku, čekáme na potvrzení termínu
    if state.get("waiting_for_confirmation"):
        # Uživatel odpoví např. "ano", "potvrzuji", "jiný termín", "zrušit"
        text = msg.lower()
        if "potvr" in text or "ano" in text:
            session_state[sid]["waiting_for_contact"] = True
            session_state[sid].pop("waiting_for_confirmation", None)
            return {"reply": f"Skvěle! Pro potvrzení mi prosím napište své jméno, email a telefon. (GDPR: Údaje slouží pouze ke kontaktování ohledně schůzky.)"}
        elif "jiný" in text or "znovu" in text or "změnit" in text:
            session_state[sid] = {"waiting_for_date": True}
            return {"reply": "Navrhněte prosím nový termín schůzky (datum a čas)."}
        elif "zrušit" in text or "nechci" in text:
            session_state[sid] = {}
            return {"reply": "Dohodnutí schůzky bylo zrušeno. Pokud si to rozmyslíte, napište mi znovu!"}
        else:
            return {"reply": "Rozumím správně? Odpovězte 'potvrzuji', 'jiný termín' nebo 'zrušit'."}

    # Čekáme na kontaktní údaje
    if state.get("waiting_for_contact"):
        success, info = parse_contact(msg)
        if success:
            meeting_time = state.get("meeting_time", "")
            log_to_airtable(
                chat_id=sid,
                question=f"Schůzka {meeting_time}",
                answer=f"{info}",
                category="MEETING"
            )
            session_state[sid] = {
                "confirmed": True,
                "meeting_time": meeting_time,
                "contacts": info
            }
            kontakty = f"{info['name']} ({info['email']}, {info['phone']})"
            return {"reply": f"Děkuji, schůzka potvrzena na {meeting_time}. Kontaktní údaje: {kontakty}.\nPokud jsou správné, napište 'OK'. Pokud chcete kontakty opravit, napište je znovu."}
        else:
            return {"reply": "Nepodařilo se rozpoznat všechny údaje. Zkuste prosím napsat své jméno, email a telefon v jednom textu."}

    # Po potvrzení kontaktů
    if state.get("confirmed"):
        if "ok" in msg.lower():
            mt = state["meeting_time"]
            info = state["contacts"]
            session_state[sid] = {}
            return {"reply": f"Vše v pořádku! Schůzka na {mt} je zarezervována. Pokud budete potřebovat změnu, napište mi. Děkuji a těším se na setkání!"}
        else:
            # Uživatel poslal nové kontakty -> zkusíme znovu rozpoznat a uložit
            success, info = parse_contact(msg)
            if success:
                mt = state["meeting_time"]
                log_to_airtable(
                    chat_id=sid,
                    question=f"Schůzka {mt} (OPRAVA)",
                    answer=f"{info}",
                    category="MEETING"
                )
                session_state[sid]["contacts"] = info
                kontakty = f"{info['name']} ({info['email']}, {info['phone']})"
                return {"reply": f"Kontaktní údaje opraveny na: {kontakty}. Pokud jsou správné, napište 'OK'."}
            else:
                return {"reply": "Znovu se nepodařilo rozpoznat kontakty. Prosím napište jméno, email a telefon v jednom textu nebo napište 'OK', pokud už je vše v pořádku."}

    # Čekáme na termín schůzky
    if state.get("waiting_for_date"):
        success, term = extract_datetime(msg)
        if success:
            # Tady můžeš v budoucnu nabídnout "dostupné časy" apod.
            session_state[sid] = {
                "waiting_for_confirmation": True,
                "meeting_time": term
            }
            return {
                "reply":
                    f"Zvolil jste termín: {term}.\nPotvrďte, prosím, jestli se Vám tento termín hodí.\n" +
                    "Odpovězte: 'potvrzuji', 'jiný termín' nebo 'zrušit'."
            }
        else:
            return {"reply": "Prosím, napište přesné datum a čas (např. 'Středa 17.7.2024 v 15:00')"}

    # První detekce intence, hlavní rozcestník
    intent = detect_intent(msg)
    if intent == "MEETING":
        session_state[sid] = {"waiting_for_date": True}
        return {"reply": "Skvěle! Navrhněte prosím konkrétní termín schůzky (datum a čas)."}

    elif intent == "CV":
        # Odpověď s odkazem na stažení souboru
        return {"reply": "Tady je mé CV:\n- [Zobrazit CV](https://telegram-hr-assistant-9i1t.onrender.com/cv)\n- [Stáhnout CV](https://telegram-hr-assistant-9i1t.onrender.com/cv)"}

    elif intent == "FAQ":
        answer = get_faq_answer(msg)
        return {"reply": answer}

    # fallback
    return {"reply": "Na tuto otázku zatím nemám odpověď, ale rád ji doplním. Zeptejte se na něco dalšího."}


# Povolení CORS (pokud chceš API volat z webu)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # produkčně zuž na ["https://portfolio-weather.onrender.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/cv")
async def get_cv():
    file_path = "source_materials/Resume_2025.pdf"
    return FileResponse(
        path=file_path,
        filename="martin-jarabek-cv.pdf",
        media_type="application/pdf"
    )