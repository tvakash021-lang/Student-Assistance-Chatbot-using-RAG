from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
import database, models
from services import ingestion, retrieval
import uuid

router = APIRouter(prefix="/api/documents", tags=["documents"])

@router.post("/upload")
async def upload_document(
    user_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db)
):
    content = await file.read()
    text = ingestion.extract_text_from_file(content, file.filename)
    chunks = ingestion.naive_chunking(text)
    
    doc_id = str(uuid.uuid4())
    db_doc = models.Document(
        id=doc_id,
        user_id=user_id,
        filename=file.filename,
        content_type=file.content_type,
        chunks_count=len(chunks)
    )
    db.add(db_doc)
    db.commit()
    
    retrieval.faiss_manager.add_chunks(chunks, source_id=doc_id)
    
    return {"message": f"Successfully uploaded and indexed {file.filename} with {len(chunks)} chunks.", "document_id": doc_id}
