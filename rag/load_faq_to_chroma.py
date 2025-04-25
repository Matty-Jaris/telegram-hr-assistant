import chromadb
import json

# Inicializace klienta Chroma (lokální embedded)
client = chromadb.Client()
collection = client.get_or_create_collection(name="faq")

# Načtení JSON s FAQ
with open("../data/faq_rag_ready.json", "r", encoding="utf-8") as f:
    faq_data = json.load(f)

# Příprava dat
documents = [item["answer"] for item in faq_data]
metadatas = [{"question": item["question"]} for item in faq_data]
ids = [str(i) for i in range(1, len(faq_data) + 1)]

# Nahrání dat do ChromaDB
collection.add(documents=documents, metadatas=metadatas, ids=ids)

print("✅ FAQ úspěšně nahráno do ChromaDB.")
