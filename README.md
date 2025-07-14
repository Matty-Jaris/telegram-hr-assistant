# 🤖 Telegram HR Assistant (FastAPI Backend)

This is the backend of a conversational HR assistant built with **FastAPI**. It handles user messages from Telegram (via n8n), helps with:

- 📅 scheduling meetings,
- 📄 sending a CV,
- ❓ answering FAQ questions,
- 🧠 fallback replies via OpenAI (GPT-4o),
- 🧾 logging interactions to Airtable,
- 📧 sending confirmation emails.

The assistant supports contextual conversations using in-memory session state (replaceable with Redis in production) and responds with either direct answers or buttons for user choices.

---

## 🚀 Features

- `/chat` — handles standard messages and manages dialog state.
- `/chat_stream` — returns streaming (word-by-word) responses.
- `/cv` — serves the CV as inline PDF.
- `/cv/download` — allows forced download of the CV.
- `/ask_stream` — fetches FAQ answers via Pinecone-based RAG model.
- `/detect_intent` — classifies messages into intent (`CV`, `MEETING`, `FAQ`).
- `/extract_date` — extracts date/time from messages via OpenAI.
- `/parse_contact` — parses contact info (name, email, phone) from free-form text.
- Integration with **Airtable** for logging, and **SMTP** for meeting notifications.

---

## 🛠️ Technologies Used

- **FastAPI** + CORS middleware
- **OpenAI GPT-4o**
- **Airtable API**
- **StreamingResponse**
- **Pinecone (via `retrieve_answer`)**
- **SMTP (email sending)**
- **n8n** (Telegram workflow orchestration)

---

## 📁 Project Structure

- `fastapi_app.py` – main app with `/chat`, `/chat_stream`, CV endpoints
- `helpers.py` – OpenAI calls, parsing logic, logging, email sending
- `router.py` – additional endpoints for structured requests
- `source_materials/Resume_2025.pdf` – served CV file

---

## 🧪 Development Notes

- Replace `session_state` with **Redis** for production use.
- `.env` file must include OpenAI key, Airtable credentials, and email config.
- All user messages are routed from Telegram (via n8n) using `chat_id` as `session_id`.

---

## 👤 Author

Martin Jarábek  
[Portfolio Website](https://portfolio-weather.onrender.com)



# 🤖 HR Asistent pro Telegram (FastAPI Backend)

Toto je backend konverzačního asistenta pro oblast HR postavený na **FastAPI**. Přijímá zprávy z Telegramu (přes n8n) a pomáhá s:

- 📅 domluvou schůzek,
- 📄 odesláním životopisu (CV),
- ❓ odpověďmi na často kladené otázky (FAQ),
- 🧠 odpověďmi přes OpenAI (GPT-4o),
- 🧾 logováním konverzací do Airtable,
- 📧 odesíláním potvrzovacích e-mailů.

Asistent podporuje kontextovou konverzaci díky session stavu (v produkci doporučeno nahradit Redisem) a vrací buď textové odpovědi, nebo tlačítka k výběru.

---

## 🚀 Funkcionalita

- `/chat` — zpracování zpráv a řízení dialogového stavu.
- `/chat_stream` — streamovaná odpověď po slovech.
- `/cv` — zobrazení CV v prohlížeči.
- `/cv/download` — stažení CV jako PDF.
- `/ask_stream` — vyhledání odpovědi z FAQ přes RAG + Pinecone.
- `/detect_intent` — rozpoznání záměru (`CV`, `MEETING`, `FAQ`).
- `/extract_date` — extrakce datumu/času ze zprávy pomocí OpenAI.
- `/parse_contact` — zpracování jména, e-mailu a telefonu z textu.
- Integrace s **Airtable** a zasílání e-mailů přes **SMTP**.

---

## 🛠️ Použité technologie

- **FastAPI** + CORS middleware
- **OpenAI GPT-4o**
- **Airtable API**
- **StreamingResponse**
- **Pinecone (dotazování přes `retrieve_answer`)**
- **SMTP (odesílání e-mailů)**
- **n8n** (workflow orchestrátor pro Telegram)

---

## 📁 Struktura projektu

- `fastapi_app.py` – hlavní server, endpointy `/chat`, `/cv`, streamování
- `helpers.py` – logika pro AI, parsování, emaily, Airtable
- `router.py` – doplňkové endpointy pro API
- `source_materials/Resume_2025.pdf` – soubor s CV

---

## 🧪 Poznámky k vývoji

- V produkčním nasazení doporučeno nahradit `session_state` Redisem.
- `.env` soubor musí obsahovat klíče pro OpenAI, Airtable a nastavení e-mailu.
- Všechny zprávy z Telegramu (přes n8n) se směrují pomocí `chat_id` jako `session_id`.

---

## 👤 Autor

Mgr. Martin Jarábek  
[Portfolio](https://portfolio-weather.onrender.com)
