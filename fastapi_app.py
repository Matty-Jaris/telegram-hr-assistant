from fastapi import FastAPI, Body
from pydantic import BaseModel
from helpers import detect_intent, extract_datetime, parse_contact, get_faq_answer, log_to_airtable
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.responses import StreamingResponse
import asyncio, json
from helpers import send_notification_email

app = FastAPI()
session_state = {}  # Na produkci raději Redis!
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://portfolio-weather.onrender.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    session_id: str

@app.post("/chat")
async def chat_handler(req: ChatRequest):
    reply, buttons = generate_reply_and_buttons(req.message.strip(), req.session_id)
    return {"reply": reply, "buttons": buttons}


def generate_reply_and_buttons(msg, sid):
    state = session_state.get(sid, {})
    reply = ""
    buttons = []

    if state.get("waiting_for_confirmation"):
        text = msg.lower()
        if "potvr" in text or "ano" in text:
            session_state[sid]["waiting_for_contact"] = True
            session_state[sid].pop("waiting_for_confirmation", None)
            reply = (
                "Skvělé, děkuji za potvrzení termínu! 📅<br><br>"
                "<b>Abychom mohli schůzku finálně domluvit, doplňte prosím své kontaktní údaje:</b><br>"
                "👤 Jméno a příjmení<br>"
                "📧 E-mailová adresa<br>"
                "📞 Telefonní číslo<br><br>"
                "Stačí vše napsat do jedné zprávy, například:<br>"
                "<i>Jan Novák, jan.novak@email.cz, 777 123 456</i><br><br>"
                "ℹ️ Vaše údaje budou použity výhradně za účelem domluvy schůzky a uchovány maximálně po dobu 30 dní."
            )
        elif "jiný" in text or "znovu" in text or "změnit" in text:
            session_state[sid] = {"waiting_for_date": True}
            reply = "Navrhněte prosím nový termín schůzky (datum a čas)."
        elif "zrušit" in text or "nechci" in text:
            session_state[sid] = {}
            reply = "Dohodnutí schůzky bylo zrušeno. Pokud si to rozmyslíte, napište mi znovu!"
        else:
            reply = "Rozumím správně? Klikněte na jedno z tlačítek.<br>"
            buttons = ["potvrzuji", "jiný termín", "zrušit"]

    elif state.get("waiting_for_contact"):
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
            reply = (
                "✅ Nová schůzka potvrzena!<br><br>"
                f"📅 Termín: <b>{meeting_time}</b><br>"
                f"👤 Jméno: <b>{info['name']}</b><br>"
                f"📞 Telefon: <b>{info['phone']}</b><br>"
                f"📧 E-mail: <b>{info['email']}</b><br><br>"
                "Pokud je vše správně, klikněte na tlačítko <b>OK</b> níže."
            )
            buttons = ["OK"]
            subject = f"Potvrzení nové schůzky: {meeting_time}"
            body = (
                f"Byla potvrzena nová schůzka:\n\n"
                f"Termín: {meeting_time}\n"
                f"Jméno: {info['name']}\n"
                f"E-mail: {info['email']}\n"
                f"Telefon: {info['phone']}\n"
            )
        else:
            reply = "Nepodařilo se rozpoznat všechny údaje.<br>Zkuste prosím napsat své jméno, email a telefon v jednom textu."

    elif state.get("confirmed"):
        if "ok" in msg.lower():
            mt = state["meeting_time"]
            info = state["contacts"]
            subject = f"Potvrzená schůzka: {mt}"
            body = (
                f"Byla potvrzena nová schůzka:\n\n"
                f"Termín: {mt}\n"
                f"Jméno: {info['name']}\n"
                f"E-mail: {info['email']}\n"
                f"Telefon: {info['phone']}\n"
            )
            send_notification_email(subject, body)
            session_state[sid] = {}
            reply = f"Vše v pořádku! Schůzka na <b>{mt}</b> je zarezervována.<br><br>Pokud budete potřebovat změnu, můžete mě kontaktovat na:<br>📞 Telefon: 727 919 163<br>📧 E-mail: martin.jar91@seznam.cz<br>Děkuji a těším se na setkání!"
        else:
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
                reply = f"Kontaktní údaje opraveny na: {kontakty}. Pokud jsou správné, klikněte na tlačítko <b>OK</b>."
                buttons = ["OK"]
            else:
                reply = "Znovu se nepodařilo rozpoznat kontakty. <br><br>Prosím napište jméno, email a telefon v jednom textu, pokud je vše správně klikněte na tlačítko <b>OK</b>."
                buttons = ["OK"]

    elif state.get("waiting_for_date"):
        success, term = extract_datetime(msg)
        if success:
            session_state[sid] = {
                "waiting_for_confirmation": True,
                "meeting_time": term
            }
            reply = (
                f"Zvolil jste termín: <b>{term}</b>.<br><br>"
                "Potvrďte prosím, jestli se vám tento termín hodí. "
                "Vyberte jednu z možností níže:<br>"
            )
            buttons = ["potvrzuji", "jiný termín", "zrušit"]
        else:
            reply = "Prosím, napište přesné datum a čas (např. 'Středa 16.7.2024 v 15:00')"

    else:
        intent = detect_intent(msg)
        if intent == "MEETING":
            session_state[sid] = {"waiting_for_date": True}
            reply = (
                "Rád se s vámi domluvím na schůzce/videohovoru.<br><br>"
                "Jelikož jsou právě letní prázdniny, jsem časově velmi flexibilní. "
                "Stačí, když mi napíšete den a čas, který vám vyhovuje.<br><br>"
                "<b><i>Například: *úterý 3.6.2025 v 15:30*</i></b><br><br>"
                "Jakmile termín napíšete, ihned vše společně domluvíme a potvrdíme."
            )
        elif intent == "CV":
            reply = (
                'Tady je mé CV:<br>'
                '<a href="https://telegram-hr-assistant-9i1t.onrender.com/cv" target="_blank" style="color:#2563eb;font-weight:bold;">Zobrazit CV</a>'
                ' &nbsp;|&nbsp; '
                '<a href="https://telegram-hr-assistant-9i1t.onrender.com/cv/download" download="martin-jarabek-cv.pdf" style="color:#2563eb;">Stáhnout CV</a>'
            )
        # elif intent == "FAQ":
        #     reply = get_faq_answer(msg)

        elif intent == "FAQ":
            reply = get_faq_answer(msg)
            if reply.strip().lower().startswith("omlouvám se"):
                log_to_airtable(
                    chat_id=sid,
                    question=msg,
                    answer=reply,
                    category="NOANSWER"
                )

        else:
            reply = "Na tuto otázku nedokážu odpovědět, zkuste ji přeformulovat, nebo se zeptat na něco dalšího."
            log_to_airtable(
                chat_id=sid,
                question=msg,
                answer=reply,
                category="NOANSWER"
            )

    return reply, buttons


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


@app.post("/chat_stream")
async def chat_stream(req: ChatRequest):
    reply, buttons = generate_reply_and_buttons(req.message.strip(), req.session_id)

    async def streamer():
        for word in reply.split(" "):
            yield word + " "
            await asyncio.sleep(0.11)
        if buttons:
            yield "\n\n[[[BUTTONS]]]" + json.dumps(buttons)
    return StreamingResponse(streamer(), media_type="text/plain")

