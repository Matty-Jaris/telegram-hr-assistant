from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from helpers import (
    get_faq_answer, detect_intent, extract_datetime, parse_contact, log_to_airtable
)
from pathlib import Path
from fastapi.responses import FileResponse

router = APIRouter()

class Question(BaseModel):
    question: str
    chat_id: str = None
    message_id: int = None

class SimpleMessage(BaseModel):
    message: str

# @router.post("/ask_stream")
# async def ask_stream(payload: Question, background_tasks: BackgroundTasks):
#     answer = get_faq_answer(payload.question)
#     background_tasks.add_task(log_to_airtable, payload.chat_id, payload.question, answer, "FAQ")
#     return {"answer": answer}

@router.post("/ask_stream")
async def ask_stream(payload: Question, background_tasks: BackgroundTasks):
    answer = get_faq_answer(payload.question)
    # Pokud není odpověď známá (podle přesného textu), logujeme jako NOANSWER
    if answer.strip().lower().startswith("omlouvám se") or answer.strip().lower().startswith("na tuto otázku nedokážu"):
        category = "NOANSWER"
    else:
        category = "FAQ"
    background_tasks.add_task(log_to_airtable, payload.chat_id, payload.question, answer, category)
    return {"answer": answer}

@router.post("/detect_intent")
async def detect_intent_endpoint(payload: SimpleMessage):
    intent = detect_intent(payload.message)
    return {"intent": intent}

@router.post("/extract_date")
async def extract_date(payload: SimpleMessage):
    success, term = extract_datetime(payload.message)
    return {"success": success, "term": term}

@router.post("/parse_contact")
async def parse_contact_info(payload: SimpleMessage):
    success, info = parse_contact(payload.message)
    return {"success": success, **info}

@app.get("/airtable_test")
def airtable_test():
    log_to_airtable("test_id", "test question", "test answer", "NOANSWER")
    return {"ok": True}






