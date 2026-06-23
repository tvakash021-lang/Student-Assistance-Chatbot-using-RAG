import os
from groq import Groq
import time
from dotenv import load_dotenv

# Load .env variables from the root directory
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

# Client initialization will be evaluated at run time so env can be set by uvicorn/dotenv
def get_groq_client():
    return Groq(api_key=os.environ.get("GROQ_API_KEY", ""))

def generate_groq_response(prompt: str, system_message: str = "You are an expert AI Academic Assistant.") -> tuple[str, float]:
    start_time = time.time()
    try:
        client = get_groq_client()
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": system_message,
                },
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="llama-3.1-8b-instant",
            response_format={"type": "json_object"},
            temperature=0.7,
            max_tokens=1024
        )
        response_text = chat_completion.choices[0].message.content
    except Exception as e:
        response_text = f"Error communicating with Groq API: {str(e)}"
    
    latency = (time.time() - start_time) * 1000
    return response_text, latency
