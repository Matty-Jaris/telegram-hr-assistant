import chromadb
import openai
from dotenv import load_dotenv
import os

load_dotenv()

# Inicializace ChromaDB
client = chromadb.Client()
collection = client.get_or_create_collection(name="faq")

# Tvůj OpenAI API klíč (doporučuju přes env proměnnou)
openai.api_key = os.getenv("OPENAI_API_KEY")

def retrieve_answer(question):
    # Vyhledání v ChromaDB
    results = collection.query(
        query_texts=[question],
        n_results=3  # můžeš upravit podle potřeby
    )

    documents = results['documents'][0]
    metadata = results['metadatas'][0]

    # Sestavení promptu pro OpenAI
    context = "\n".join([f"Q: {meta['question']}\nA: {doc}" for meta, doc in zip(metadata, documents)])
    prompt = f"Následují otázky a odpovědi z FAQ:\n{context}\n\nDotaz: {question}\nOdpověz co nejpřesněji na základě těchto dat:"

    # OpenAI odpověď
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Odpovídáš na základě znalostí z FAQ. Pokud odpověď není v datech, řekni, že nemáš informace."},
            {"role": "user", "content": prompt}
        ]
    )

    return response['choices'][0]['message']['content']

if __name__ == "__main__":
    user_question = input("Zadej dotaz: ")
    answer = retrieve_answer(user_question)
    print("🟢 Odpověď:", answer)
