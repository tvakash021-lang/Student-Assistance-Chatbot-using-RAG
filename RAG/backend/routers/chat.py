from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session
import schemas, database
from services import llm, memory, retrieval

router = APIRouter(prefix="/api/chat", tags=["chat"])

@router.post("/", response_model=schemas.ChatResponse)
def chat_endpoint(request: schemas.ChatRequest, db: Session = Depends(database.get_db)):
    session = memory.get_or_create_session(db, request.user_id, request.session_id)
    memory.add_message(db, session.id, "user", request.message)
    
    # 1. Retrieve context
    docs = retrieval.faiss_manager.search(request.message, top_k=3)
    context_chunks = "\n---\n".join([doc["chunk"] for doc in docs])
    
    # 2. Get hitstory
    history = memory.get_history(db, session.id, limit=5)
    history_text = "\n".join([f"{msg.role}: {msg.content}" for msg in history])
    
    # 3. Create prompt
    system_prompt = f"""You are an AI Academic Assistant powered by a Retrieval-Augmented Generation (RAG) system.

You are integrated with:
- A vector database (FAISS) for retrieving relevant document chunks
- A conversation memory system (chat history)
- A Text-to-Speech (TTS) pipeline (Kokoro)
- A word-alignment system (WhisperX) for highlighting

Your task is to generate accurate, structured, and speech-friendly responses.

━━━━━━━━━━━━━━━━━━━━━━━
1. CONTEXT USAGE (STRICT RAG)
━━━━━━━━━━━━━━━━━━━━━━━
You will be given:
- Retrieved document context
- Previous conversation history

Rules:
- If the answer exists in the provided context:
  → Answer ONLY using that information
- Do NOT add external knowledge
- If the answer is NOT explicitly present:
  → Respond EXACTLY: "This information is not available in the provided data."
  → Do NOT guess or infer

━━━━━━━━━━━━━━━━━━━━━━━
2. CONVERSATIONAL MEMORY
━━━━━━━━━━━━━━━━━━━━━━━
- Use previous messages to maintain continuity
- For follow-up questions:
  → Refer to earlier answers when needed
- Avoid repeating the same explanation unless necessary

━━━━━━━━━━━━━━━━━━━━━━━
3. RESPONSE QUALITY
━━━━━━━━━━━━━━━━━━━━━━━
- Keep answers between 3 to 8 sentences
- Prefer clarity over complexity
- Use:
  - bullet points for lists
  - step-by-step explanations for processes
- Avoid unnecessary technical jargon unless asked

━━━━━━━━━━━━━━━━━━━━━━━
4. OUTPUT FORMAT (STRICT JSON)
━━━━━━━━━━━━━━━━━━━━━━━
Return ONLY valid JSON. No extra text.

{{
  "text_response": "<clean, structured answer for UI display>",
  "tts_text": "<speech-optimized version of the same answer>",
  "metadata": {{
    "source_used": true,
    "confidence": "high"
  }}
}}

━━━━━━━━━━━━━━━━━━━━━━━
5. TTS OPTIMIZATION (CRITICAL)
━━━━━━━━━━━━━━━━━━━━━━━
For "tts_text":
- Use short, natural sentences
- Avoid long paragraphs
- Use proper punctuation for pauses
- Expand abbreviations: AI → Artificial Intelligence, ML → Machine Learning
- Do NOT include: emojis, special symbols, markdown formatting

━━━━━━━━━━━━━━━━━━━━━━━
6. ALIGNMENT COMPATIBILITY (WHISPERX)
━━━━━━━━━━━━━━━━━━━━━━━
- The system will generate audio and align words later
- DO NOT generate timestamps
- Words in "tts_text" are clean and consistent
- Avoid unusual characters or formatting
- Keep wording simple for accurate alignment

━━━━━━━━━━━━━━━━━━━━━━━
7. FALLBACK HANDLING
━━━━━━━━━━━━━━━━━━━━━━━
If no relevant context is found:
- Respond with the required fallback sentence
- Optionally guide the user on what to ask next

━━━━━━━━━━━━━━━━━━━━━━━
8. ERROR HANDLING
━━━━━━━━━━━━━━━━━━━━━━━
- If the query is unclear:
  → Ask a clarification question
- Do not produce misleading or fabricated information

━━━━━━━━━━━━━━━━━━━━━━━
9. STRICT RULES
━━━━━━━━━━━━━━━━━━━━━━━
- ALWAYS return valid JSON
- NO text outside JSON
- DO NOT hallucinate
- DO NOT skip fields
- Ensure both "text_response" and "tts_text" are meaningful

    Chat History:
    {history_text}
    
    Retrieved Context:
    {context_chunks}
    """
    
    import json
    # 4. Generate
    response_text_raw, latency = llm.generate_groq_response(request.message, system_message=system_prompt)
    
    try:
        response_json = json.loads(response_text_raw)
        text_response = response_json.get("text_response", "")
        metadata_dict = response_json.get("metadata", {"source_used": False, "confidence": "low"})
        
        # Override tts_text to guarantee it contains exactly the same words as text_response
        # Replace markdown symbols and newlines with commas so TTS reads it smoothly without crashing
        import re
        tts_text = re.sub(r'[*`#_>-]', ',', text_response)
        tts_text = tts_text.replace('\n', ' ')
    except json.JSONDecodeError:
        text_response = "Sorry, I had an internal error generating the correct format. Raw Output:\n" + response_text_raw
        tts_text = text_response
        metadata_dict = {"source_used": False, "confidence": "error"}

    # 5. Save response
    memory.add_message(db, session.id, "assistant", text_response)
    
    # 6. Audio Generation
    audio_url = None
    timestamps = []
    if tts_text:
        try:
            from services import audio
            import os
            audio_path = audio.synthesize_audio(tts_text, session.id)
            if audio_path:
                timestamps = audio.extract_timestamps(audio_path, tts_text)
                audio_url = f"/data/audio/{os.path.basename(audio_path)}"
        except ImportError as e:
            print(f"Audio dependencies not installed. Skipping TTS. Error: {e}")
        except Exception as e:
            print(f"Audio generation failed: {e}")
            
    return schemas.ChatResponse(
        session_id=session.id,
        text_response=text_response,
        tts_text=tts_text,
        metadata=schemas.ChatMetadata(**metadata_dict),
        audio_url=audio_url,
        timestamps=timestamps,
        latency_ms=latency
    )

@router.get("/sessions/{user_id}", response_model=list[schemas.Session])
def get_sessions(user_id: str, db: Session = Depends(database.get_db)):
    sessions = memory.get_user_sessions(db, user_id)
    return sessions

@router.get("/history/{session_id}", response_model=list[schemas.Message])
def get_session_history(session_id: str, db: Session = Depends(database.get_db)):
    history = memory.get_history(db, session_id, limit=100)
    return history

@router.post("/audio_transcribe")
async def transcribe_audio_endpoint(file: UploadFile = File(...)):
    try:
        import os
        import uuid
        from services import audio
        
        os.makedirs("data/audio", exist_ok=True)
        temp_path = f"data/audio/stt_{uuid.uuid4().hex[:8]}.wav"
        with open(temp_path, "wb") as f:
            f.write(await file.read())
            
        text = audio.transcribe_audio(temp_path)
        
        try:
            os.remove(temp_path)
        except:
            pass
            
        return {"text": text}
    except Exception as e:
        import traceback
        return {"text": f"[ERROR] Backend Endpoint crashed: {str(e)}\n{traceback.format_exc()}"}

@router.post("/synthesize", response_model=schemas.SynthesizeResponse)
def synthesize_endpoint(req: schemas.SynthesizeRequest):
    import re
    import os
    from services import audio
    
    # Clean the text exactly like we do in the chat loop
    tts_text = re.sub(r'[*`#_>-]', ',', req.text)
    tts_text = tts_text.replace('\n', ' ')
    
    audio_url = ""
    timestamps = []
    
    try:
        audio_path = audio.synthesize_audio(tts_text, "synthesize")
        if audio_path:
            timestamps = audio.extract_timestamps(audio_path, tts_text)
            audio_url = f"/data/audio/{os.path.basename(audio_path)}"
    except ImportError as e:
        print(f"Audio dependencies not installed. Skipping TTS. Error: {e}")
    except Exception as e:
        print(f"Audio generation failed: {e}")
        
    return schemas.SynthesizeResponse(
        audio_url=audio_url,
        timestamps=timestamps
    )
