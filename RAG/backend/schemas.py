from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class MessageBase(BaseModel):
    role: str
    content: str

class MessageCreate(MessageBase):
    pass

class Message(MessageBase):
    id: int
    session_id: str
    created_at: datetime
    class Config:
        from_attributes = True

class SessionBase(BaseModel):
    title: str

class SessionCreate(SessionBase):
    user_id: str

class Session(SessionBase):
    id: str
    user_id: str
    created_at: datetime
    messages: List[Message] = []
    class Config:
        from_attributes = True

class ChatRequest(BaseModel):
    user_id: str
    session_id: Optional[str] = None
    message: str

class ChatMetadata(BaseModel):
    source_used: bool
    confidence: str

class ChatResponse(BaseModel):
    session_id: str
    text_response: str
    tts_text: str
    metadata: ChatMetadata
    audio_url: Optional[str] = None
    timestamps: List[Dict[str, Any]] = []
    latency_ms: float

class SynthesizeRequest(BaseModel):
    text: str

class SynthesizeResponse(BaseModel):
    audio_url: str
    timestamps: List[Dict[str, Any]] = []
