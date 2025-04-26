# from fastapi import FastAPI
# from pydantic import BaseModel
# from rag.query_from_pinecone import retrieve_answer

# app = FastAPI()

# class QueryRequest(BaseModel):
#     question: str

# @app.post("/ask")
# async def ask_question(request: QueryRequest):
#     answer = retrieve_answer(request.question)
#     return {"answer": answer}

from fastapi import FastAPI
from pydantic import BaseModel
from rag.query_from_pinecone import retrieve_answer

app = FastAPI()

class QueryRequest(BaseModel):
    question: str

@app.post("/ask")
async def ask_question(request: QueryRequest):
    try:
        answer = retrieve_answer(request.question)
        return {"answer": answer}
    except Exception as e:
        return {"error": str(e)}

