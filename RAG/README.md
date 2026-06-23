# AI Academic Assistant

A complete, scalable, and modular AI Academic Assistant featuring Adaptive Retrieval, Persistent Chat Memory, and Learning Analytics.

## Architecture

- **Frontend**: Streamlit
- **Backend API**: FastAPI
- **Vector Database**: FAISS (local) & Sentence Transformers (`all-MiniLM-L6-v2`)
- **Memory Store**: SQLite & SQLAlchemy (Ready to switch to PostgreSQL)
- **LLM Engine**: Groq API (`llama3-8b-8192` for fast inference)

## Setup Instructions

### 1. Pre-requisites
- Python 3.10+
- Groq API Key (Free tier works!)

### 2. Environment Variables
Copy `.env.example` to `.env` and fill in your Groq API key:
```bash
cp .env.example .env
```
Ensure you have `GROQ_API_KEY=your_key` in `.env`.

### 3. Local Execution (No Docker)

**Shell 1: Start the Backend (FastAPI)**
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```
*Wait for the application to start up (takes a few seconds to load the embedding models into memory).*

**Shell 2: Start the Frontend (Streamlit)**
```bash
cd frontend
pip install -r requirements.txt
streamlit run app.py
```

### 4. Docker Compose Execution (Recommended for Production)

Make sure Docker is installed.
```bash
docker-compose up --build
```
- Access API at `http://localhost:8000/docs`
- Access App at `http://localhost:8501`

### Application Workflow
1. Upload a PDF/DOCX file from the Sidebar. Data is chunked and stored in FAISS and SQLite.
2. Ask questions. The context engine retrieves the top chunks using Sentence Transformers.
3. The Chat Router pulls your 5 most recent chat memory exchanges from the SQLite database.
4. The system injects the Context + History into the Groq API model.
5. The result is streamed back into the Streamlit app.
