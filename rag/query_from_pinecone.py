import os
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

# Normalizace textu
def normalize(text):
    return text.strip().lower()

def get_embedding(text):
    text = normalize(text)
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

def retrieve_answer(question):
    query_vector = get_embedding(question)

    print("🔍 Hledám podobné otázky v Pinecone...")
    search_result = index.query(
        vector=query_vector,
        top_k=3,
        include_metadata=True
    )

    matches = search_result.matches
    if not matches:
        return "❌ V databázi FAQ jsem nenašel odpověď na tuto otázku."

    context = "\n".join([
        f"Q: {match['metadata']['question']}\nA: {match['metadata']['answer']}"
        for match in matches
    ])

    prompt = f"Následují otázky a odpovědi z FAQ:\n{context}\n\nDotaz: {question}\nOdpověz co nejpřesněji na základě těchto dat:"

    print("🤖 Generuji odpověď pomocí OpenAI...")
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Odpovídáš na základě znalostí z FAQ. Pokud odpověď není v datech, řekni, že nemáš informace."},
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].message.content

if __name__ == "__main__":
    print("🟢 FAQ asistent je připraven! Zadej svou otázku:")
    while True:
        try:
            user_question = input("\n❓ Zadej dotaz (nebo 'exit' pro ukončení): ")
            if user_question.lower() == 'exit':
                print("👋 Ukončuji. Měj se fajn!")
                break
            print("⏳ Pracuji na odpovědi...")
            answer = retrieve_answer(user_question)
            print("\n🟢 Odpověď:", answer)
        except KeyboardInterrupt:
            print("\n👋 Ukončuji. Měj se fajn!")
            break
