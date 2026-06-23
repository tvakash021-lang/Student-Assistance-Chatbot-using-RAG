from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from database import engine, Base
from routers import chat, documents

os.makedirs("data/audio", exist_ok=True)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Academic Assistant API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/data/audio", StaticFiles(directory="data/audio"), name="audio")

app.include_router(chat.router)
app.include_router(documents.router)

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Welcome to the AI Academic Assistant API"}
