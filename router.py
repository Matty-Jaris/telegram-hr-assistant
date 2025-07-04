from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from helpers import (
    get_faq_answer, detect_intent, extract_datetime, parse_contact, log_to_airtable
)
from pathlib import Path

router = APIRouter()

WELCOME_PATH = Path("prompts/welcome_message.md")
if WELCOME_PATH.exists():
    WELCOME_MSG = WELCOME_PATH.read_text(encoding="utf-8")
else:
    WELCOME_MSG = "**Welcome message nenalezen.**"

@router.get("/welcome")
async def get_welcome():
    """
    Vrátí statickou uvítací zprávu.
    """
    return {"welcome": WELCOME_MSG}


    

class Question(BaseModel):
    question: str
    chat_id: str = None
    message_id: int = None

class SimpleMessage(BaseModel):
    message: str

@router.post("/ask_stream")
async def ask_stream(payload: Question, background_tasks: BackgroundTasks):
    answer = get_faq_answer(payload.question)
    background_tasks.add_task(log_to_airtable, payload.chat_id, payload.question, answer, "FAQ")
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

from fastapi.responses import FileResponse



