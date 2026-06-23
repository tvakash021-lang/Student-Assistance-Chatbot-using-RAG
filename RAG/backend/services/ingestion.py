import PyPDF2
import docx
import io

def extract_text_from_file(file_bytes: bytes, filename: str) -> str:
    text = ""
    if filename.endswith(".pdf"):
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
    elif filename.endswith(".docx"):
        doc = docx.Document(io.BytesIO(file_bytes))
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
    elif filename.endswith(".txt"):
        text = file_bytes.decode("utf-8")
    return text

def naive_chunking(text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
    chunks = []
    start = 0
    text_length = len(text)
    while start < text_length:
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks
