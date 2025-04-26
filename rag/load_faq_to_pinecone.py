import os
import json
from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone

# Načtení API klíčů
load_dotenv()
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index("faq-assistant")

# Normalizace textu (malá písmena + trim mezer)
def normalize(text):
    return text.strip().lower()

def get_embedding(text):
    text = normalize(text)
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

with open("data/faq_rag_ready.json", "r", encoding="utf-8") as f:
    faq_data = json.load(f)

vectors_to_upsert = []
print(f"🔄 Připravuji {len(faq_data)} položek k nahrání...")

for i, item in enumerate(faq_data):
    vector = get_embedding(item["question"])
    vectors_to_upsert.append((str(i), vector, {"question": item["question"], "answer": item["answer"]}))
    print(f"✅ Vygenerováno pro otázku: {item['question']}")

print("🚀 Nahrávám vektory do Pinecone...")
index.upsert(vectors=vectors_to_upsert)
print("✅ Data byla nahrána!")

# Kontrola
describe = index.describe_index_stats()
print("\n📦 Index info:")
print(describe.to_dict())

