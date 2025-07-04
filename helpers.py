import openai, os, re, json
from airtable import Airtable
from rag.query_from_pinecone import retrieve_answer
from datetime import datetime

openai.api_key = os.getenv("OPENAI_API_KEY")
airtable = Airtable(os.getenv("AIRTABLE_BASE"), "HR Assistant Logs", os.getenv("AIRTABLE_TOKEN"))

def get_faq_answer(question):
    answer = retrieve_answer(question)
    return answer or "Omlouvám se, zatím nemám odpověď."

def detect_intent(message):
    if re.search(r"(cv|životopis)", message, re.I):
        return "CV"
    elif re.search(r"(schůzk|pohovor|call|setkat)", message, re.I):
        return "MEETING"
    return "FAQ"

def extract_datetime(message):
    prompt = "Extrahuj termín (DD.MM.YYYY HH:mm) nebo NEPLATNÉ."
    response = openai.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt + message}], temperature=0)
    term = response.choices[0].message.content.strip()
    return (term != "NEPLATNÉ", term if term != "NEPLATNÉ" else None)

def parse_contact(message):
    prompt = (
        "Z následující zprávy extrahuj jméno, email a telefonní číslo. "
        "Vrať pouze validní JSON ve formátu: "
        '{"name": "...", "email": "...", "phone": "..."}\n'
        "Nevypisuj žádné další komentáře, pouze JSON!"
        f"\nZpráva: {message}"
    )
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=100
    )
    content = response.choices[0].message.content.strip()
    try:
        # Najdi JSON v odpovědi (pro jistotu vyber první {...})
        import re, json
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if not match:
            return False, {}
        data = json.loads(match.group(0))
        return True, data
    except Exception as e:
        print("Chyba při parsování kontaktu:", content, e)
        return False, {}


def log_to_airtable(chat_id, question, answer, category):
    airtable.insert({"Chat ID": chat_id, "Question": question, "Answer": answer, "Category": category, "Timestamp": datetime.now().isoformat()})
