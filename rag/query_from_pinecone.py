# import os
# from dotenv import load_dotenv
# from openai import OpenAI
# from pinecone import Pinecone

# # Načtení API klíčů
# load_dotenv()
# PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
# PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT")
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# client = OpenAI(api_key=OPENAI_API_KEY)
# pc = Pinecone(api_key=PINECONE_API_KEY)
# index = pc.Index("faq-assistant")

# # Normalizace textu
# def normalize(text):
#     return text.strip().lower()

# def get_embedding(text):
#     text = normalize(text)
#     response = client.embeddings.create(
#         model="text-embedding-3-small",
#         input=[text]  # musí být seznam!
#     )
#     return response.data[0].embedding


# def retrieve_answer(question):
#     query_vector = get_embedding(question)

#     print("🔍 Hledám podobné otázky v Pinecone...")
#     search_result = index.query(
#         vector=query_vector,
#         top_k=3,
#         include_metadata=True
#     )

#     matches = search_result.matches
#     if not matches:
#         print("⚠️ Nenašel jsem odpověď v FAQ, používám fallback OpenAI...")
#         response = client.chat.completions.create(
#             model="gpt-4o",
#             messages=[
#                 {"role": "system", "content": "Odpovídáš na otázky, pokud nejsou v databázi FAQ."},
#                 {"role": "user", "content": question}
#             ]
#         )
#         return response.choices[0].message.content


#     context = "\n".join([
#         f"Q: {match['metadata']['question']}\nA: {match['metadata']['answer']}"
#         for match in matches
#     ])

#     prompt = f"Následují otázky a odpovědi z FAQ:\n{context}\n\nDotaz: {question}\nOdpověz co nejpřesněji na základě těchto dat:"

#     print("🤖 Generuji odpověď pomocí OpenAI...")
#     response = client.chat.completions.create(
#         model="gpt-4o",
#         messages=[
#             {"role": "system", "content": "Odpovídáš na základě znalostí z FAQ. Pokud odpověď není v datech, řekni, že nemáš informace."},
#             {"role": "user", "content": prompt}
#         ]
#     )

#     return response.choices[0].message.content

# if __name__ == "__main__":
#     print("🟢 FAQ asistent je připraven! Zadej svou otázku:")
#     while True:
#         try:
#             user_question = input("\n❓ Zadej dotaz (nebo 'exit' pro ukončení): ")
#             if user_question.lower() == 'exit':
#                 print("👋 Ukončuji. Měj se fajn!")
#                 break
#             print("⏳ Pracuji na odpovědi...")
#             answer = retrieve_answer(user_question)
#             print("\n🟢 Odpověď:", answer)
#         except KeyboardInterrupt:
#             print("\n👋 Ukončuji. Měj se fajn!")
#             break

import os
from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone

load_dotenv()
PINECONE_API_KEY       = os.getenv("PINECONE_API_KEY")
PINECONE_ENVIRONMENT   = os.getenv("PINECONE_ENVIRONMENT")
OPENAI_API_KEY         = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)
pc     = Pinecone(api_key=PINECONE_API_KEY)
index  = pc.Index("faq-assistant")


def normalize(text: str) -> str:
    return text.strip().lower()

def get_embedding(text):
    text = normalize(text)
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=[text]
    )
    return response.data[0].embedding


def retrieve_answer(question: str) -> str:
    if normalize(question) in {"ano", "jo", "jasně", "jasne", "určitě", "souhlasím"}:
        return ("Pardon, nejsem si jistý, na co odpovídáte. "
                "Můžete prosím zopakovat dotaz nebo položit další otázku?")

    
    query_vector = get_embedding(question)

    search_result = index.query(
        vector=query_vector,
        top_k=3,
        include_metadata=True
    )

    matches = search_result.matches
    if not matches:
        # 🔸 Fallback OpenAI (když v Pinecone nic není)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Odpovídáš na otázky ohledně Martina, jeho projektů a zkušeností. "
                        "**Pokud odpověď neznáš nebo není v dostupných datech, "
                        "napiš: 'Omlouvám se, nejsem si jistý odpovědí. "
                        "Zkuste prosím otázku přeformulovat, nebo se zeptejte na něco jiného.'**"
                    )
                },
                {"role": "user", "content": question}
            ]
        )
        return response.choices[0].message.content

    # 3 nejlepší shody → kontext
    context = "\n".join([
        f"Q: {m['metadata']['question']}\nA: {m['metadata']['answer']}"
        for m in matches
    ])

    prompt = (
        f"Následují otázky a odpovědi z FAQ:\n{context}\n\n"
        f"Dotaz: {question}\n"
        f"Odpověz co nejpřesněji na základě těchto dat:"
    )

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "Odpovídáš pouze na základě poskytnutých FAQ záznamů. "
                    "**Pokud v těchto datech odpověď není, odpověz: "
                    "'Omlouvám se, nejsem si jistý odpovědí. "
                    "Zkuste prosím otázku přeformulovat, nebo se zeptejte na něco jiného.'**"
                )
            },
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content


if __name__ == "__main__":
    print("🟢 FAQ asistent je připraven! Zadej svou otázku:")
    while True:
        try:
            q = input("\n❓ Zadej dotaz (nebo 'exit'): ")
            if q.lower() == "exit":
                break
            print("⏳ Pracuji na odpovědi…")
            print("\n🟢 Odpověď:", retrieve_answer(q))
        except KeyboardInterrupt:
            break


