from sqlalchemy.orm import Session
import uuid
import sys
import os
import models, schemas

def get_or_create_session(db: Session, user_id: str, session_id: str = None) -> models.Session:
    if session_id:
        session = db.query(models.Session).filter(models.Session.id == session_id).first()
        if session:
            return session
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        user = models.User(id=user_id)
        db.add(user)
        db.commit()
        db.refresh(user)
        
    new_session_id = str(uuid.uuid4())
    db_session = models.Session(id=new_session_id, user_id=user_id)
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session

def add_message(db: Session, session_id: str, role: str, content: str):
    db_message = models.Message(session_id=session_id, role=role, content=content)
    db.add(db_message)
    db.commit()
    db.refresh(db_message)

def get_history(db: Session, session_id: str, limit: int = 5) -> list[models.Message]:
    messages = db.query(models.Message).filter(models.Message.session_id == session_id).order_by(models.Message.created_at.desc()).limit(limit).all()
    return messages[::-1]  # Return in chronological order

def get_user_sessions(db: Session, user_id: str) -> list[models.Session]:
    return db.query(models.Session).filter(models.Session.user_id == user_id).order_by(models.Session.created_at.desc()).all()
