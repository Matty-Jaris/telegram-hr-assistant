import os
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec

# Načtení API klíčů z .env
load_dotenv()
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT")

# Inicializace Pinecone klienta
pc = Pinecone(api_key=PINECONE_API_KEY)
INDEX_NAME = "faq-assistant"

# Smazání starého indexu, pokud existuje
if INDEX_NAME in pc.list_indexes().names():
    print(f"🛑 Mažu starý index '{INDEX_NAME}'...")
    pc.delete_index(INDEX_NAME)
else:
    print(f"✅ Index '{INDEX_NAME}' zatím neexistoval.")

# Znovuvytvoření indexu
print(f"🚀 Vytvářím nový index '{INDEX_NAME}'...")
pc.create_index(
    name=INDEX_NAME,
    dimension=1536,                # Musí odpovídat modelu text-embedding-3-small
    metric="cosine",
    spec=ServerlessSpec(
        cloud="aws",               # Free tier je AWS
        region=PINECONE_ENVIRONMENT  # Např. 'us-east-1'
    )
)

print(f"✅ Index '{INDEX_NAME}' byl úspěšně vytvořen!")

# Ověření, že index existuje
print("📦 Aktuální indexy:", pc.list_indexes().names())
