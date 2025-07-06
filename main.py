from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import openai
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.get("/")
async def root():
    return {"message": "Welcome to the ChatBot API"}

class ChatRequest(BaseModel):
    message: str
    lang: str = "en"

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    # System prompt to constrain assistant to hotel booking only
    system_prompt = """
    You are a vacation assistant. ONLY answer questions about booking hotels or vacation stays.
    If the user asks for a location, date, or preference, suggest an Airbnb link like:
    https://www.airbnb.com/s/{city}/homes?checkin={checkin}&checkout={checkout}

    Example:
    User: I want a hotel in Paris from July 12 to July 14
    You: Sure! Here's a link to browse stays in Paris from July 12 to July 14:
    https://www.airbnb.com/s/Paris--France/homes?checkin=2025-07-12&checkout=2025-07-14

    ❌ If the question is NOT about vacation or hotel booking, respond with:
    "❌ I'm sorry, I can only help with hotel bookings and vacation-related inquiries."
    """

    chat_completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": request.message},
        ]
    )

    return {
        "response": chat_completion.choices[0].message.content
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
