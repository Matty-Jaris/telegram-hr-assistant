from fastapi import FastAPI, Body
from pydantic import BaseModel
from helpers import detect_intent, extract_datetime, parse_contact, get_faq_answer, log_to_airtable
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from helpers import send_notification_email

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
            return {"reply": (
                        "Skvělé, děkuji za potvrzení termínu! 📅<br><br>"
                        "<b>Abychom mohli schůzku finálně domluvit, doplňte prosím své kontaktní údaje:</b><br>"
                        "👤 Jméno a příjmení<br>"
                        "📧 E-mailová adresa<br>"
                        "📞 Telefonní číslo<br><br>"
                        "Stačí vše napsat do jedné zprávy, například:<br>"
                        "<i>Jan Novák, jan.novak@email.cz, 777 123 456</i><br><br>"
                        "ℹ️ Vaše údaje budou použity výhradně za účelem domluvy schůzky a uchovány maximálně po dobu 30 dní."
                    )
            }
        elif "jiný" in text or "znovu" in text or "změnit" in text:
            session_state[sid] = {"waiting_for_date": True}
            return {"reply": "Navrhněte prosím nový termín schůzky (datum a čas)."}
        elif "zrušit" in text or "nechci" in text:
            session_state[sid] = {}
            return {"reply": "Dohodnutí schůzky bylo zrušeno. Pokud si to rozmyslíte, napište mi znovu!"}
        
        else:
        # Nabídni tlačítka!
            return {
                "reply": "Rozumím správně? Klikněte na jedno z tlačítek.<br>",
                "buttons": ["potvrzuji", "jiný termín", "zrušit"]
            }

    # Čekáme na kontaktní údaje
    if state.get("waiting_for_contact"):
        success, info = parse_contact(msg)
        if success:
            meeting_time = state.get("meeting_time", "")
            log_to_airtable(
                chat_id=sid,
                question=f"Schůzka {meeting_time}",
                answer=info,
                category="MEETING",
                term=meeting_time
            )
            session_state[sid] = {
                "confirmed": True,
                "meeting_time": meeting_time,
                "contacts": info
            }
            kontakty = f"{info['name']} ({info['email']}, {info['phone']})"
            return {
                "reply": (
                    "✅ Nová schůzka potvrzena!<br><br>"
                    f"📅 Termín: <b>{meeting_time}</b><br>"
                    f"👤 Jméno: <b>{info['name']}</b><br>"
                    f"📞 Telefon: <b>{info['phone']}</b><br>"
                    f"📧 E-mail: <b>{info['email']}</b><br><br>"
                    "Pokud je vše správně, klikněte na tlačítko <b>OK</b> níže."
                ),
                "buttons": ["OK"]
            }
            
        else:
            return {"reply": "Nepodařilo se rozpoznat všechny údaje.<br>Zkuste prosím napsat své jméno, email a telefon v jednom textu."}

    # Po potvrzení kontaktů
    if state.get("confirmed"):
        if "ok" in msg.lower():
            mt = state["meeting_time"]
            info = state["contacts"]
            session_state[sid] = {}
            send_notification_email(
                subject="Nová schůzka potvrzena",
                body=(
                    f"Potvrzena nová schůzka\n"
                    f"Termín: {mt}\n"
                    f"Jméno: {info['name']}\n"
                    f"E-mail: {info['email']}\n"
                    f"Telefon: {info['phone']}"
                )
            )
            return {"reply": f"Vše v pořádku! Schůzka na <b>{mt}</b> je zarezervována.<br><br>Pokud budete potřebovat změnu, můžete mě kontaktovat na:<br>📞 Telefon: 727 919 163<br>📧 E-mail: martin.jar91@seznam.cz<br>Děkuji a těším se na setkání!"}
        else:
            # Uživatel poslal nové kontakty -> zkusíme znovu rozpoznat a uložit
            success, info = parse_contact(msg)
            if success:
                mt = state["meeting_time"]
                log_to_airtable(
                    chat_id=sid,
                    question=f"Schůzka {mt} (OPRAVA)",
                    answer=info,
                    category="MEETING"
                )
                session_state[sid]["contacts"] = info
                kontakty = f"{info['name']} ({info['email']}, {info['phone']})"
                return {
                    "reply": f"Kontaktní údaje opraveny na: {kontakty}. Pokud jsou správné, klikněte na tlačítko <b>OK</b>.",
                    "buttons": ["OK"]
                }
            else:
                return {
                    "reply": "Znovu se nepodařilo rozpoznat kontakty. <br><br>Prosím napište jméno, email a telefon v jednom textu, pokud je vše správně klikněte na tlačítko <b>OK</b>.",
                    "buttons": ["OK"]
                }


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
                "reply": (
                    f"Zvolil jste termín: <b>{term}</b>.<br><br>"
                    "Potvrďte prosím, jestli se vám tento termín hodí. "
                    "Vyberte jednu z možností níže:<br>"
                ),
                "buttons": ["potvrzuji", "jiný termín", "zrušit"]
            }
        else:
            return {"reply": "Prosím, napište přesné datum a čas (např. 'Středa 16.7.2024 v 15:00')"}

    # První detekce intence, hlavní rozcestník
    intent = detect_intent(msg)
    if intent == "MEETING":
        session_state[sid] = {"waiting_for_date": True}
        return {"reply": (
                    "Rád se s vámi domluvím na schůzce/videohovoru.<br><br>"
                    "Jelikož jsou právě letní prázdniny, jsem časově velmi flexibilní. "
                    "Stačí, když mi napíšete den a čas, který vám vyhovuje.<br><br>"
                    "<b><i>Například: *úterý 3.6.2025 v 15:30*</i></b><br><br>"
                    "Jakmile termín napíšete, ihned vše společně domluvíme a potvrdíme."
                )
        }


    elif intent == "CV":
    # Odpověď s odkazem na stažení souboru
        return {
            "reply": (
                'Tady je mé CV:<br>'
                '<a href="https://telegram-hr-assistant-9i1t.onrender.com/cv" target="_blank" style="color:#2563eb;font-weight:bold;">Zobrazit CV</a>'
                ' &nbsp;|&nbsp; '
                '<a href="https://telegram-hr-assistant-9i1t.onrender.com/cv/download" download="martin-jarabek-cv.pdf" style="color:#2563eb;">Stáhnout CV</a>'
            )
        }




    elif intent == "FAQ":
        answer = get_faq_answer(msg)
        return {"reply": answer}

    # fallback
    return {"reply": "Na tuto otázku nedokážu odpovědět, zkuste ji přeformulovat, nebo se zeptat na něco dalšího."}


# Povolení CORS (pokud chceš API volat z webu)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # produkčně zuž na ["https://portfolio-weather.onrender.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.responses import FileResponse

@app.get("/cv")
async def get_cv():
    # Zobrazení v prohlížeči (inline)
    file_path = "source_materials/Resume_2025.pdf"
    headers = {
        "Content-Disposition": 'inline; filename="martin-jarabek-cv.pdf"'
    }
    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        headers=headers
    )

@app.get("/cv/download")
async def download_cv():
    # Vynucené stažení
    file_path = "source_materials/Resume_2025.pdf"
    headers = {
        "Content-Disposition": 'attachment; filename="martin-jarabek-cv.pdf"'
    }
    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        headers=headers
    )
