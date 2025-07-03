from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from router import router as chatbot_router

app = FastAPI()

# Povolení CORS pro komunikaci s portfoliem
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # v produkci nastav na ["https://portfolio-weather.onrender.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chatbot_router, prefix="/chatbot_api")
