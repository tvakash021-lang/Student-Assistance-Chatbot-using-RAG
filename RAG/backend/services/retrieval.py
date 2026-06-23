import faiss
from sentence_transformers import SentenceTransformer
import numpy as np
import os
import pickle

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
# Lazy load model to speed up startup
embedding_model = None

def get_embedding_model():
    global embedding_model
    if embedding_model is None:
        embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return embedding_model

class FAISSManager:
    def __init__(self, index_path="./data/faiss_index.bin", metadata_path="./data/faiss_meta.pkl"):
        self.index_path = index_path
        self.metadata_path = metadata_path
        self.dimension = 384 # Dimension for all-MiniLM-L6-v2
        self.index = self._load_index()
        self.metadata = self._load_metadata()
    
    def _load_index(self):
        if os.path.exists(self.index_path):
            return faiss.read_index(self.index_path)
        return faiss.IndexFlatL2(self.dimension)
    
    def _load_metadata(self):
        if os.path.exists(self.metadata_path):
            with open(self.metadata_path, "rb") as f:
                return pickle.load(f)
        return []
    
    def save(self):
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        faiss.write_index(self.index, self.index_path)
        with open(self.metadata_path, "wb") as f:
            pickle.dump(self.metadata, f)

    def add_chunks(self, chunks: list[str], source_id: str):
        if not chunks:
            return
        model = get_embedding_model()
        embeddings = model.encode(chunks)
        
        self.index.add(np.array(embeddings).astype("float32"))
        for chunk in chunks:
            self.metadata.append({"source_id": source_id, "text": chunk})
        
        self.save()

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        if self.index.ntotal == 0:
            return []
        model = get_embedding_model()
        query_vector = model.encode([query]).astype("float32")
        distances, indices = self.index.search(query_vector, top_k)
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx != -1 and idx < len(self.metadata):
                results.append({
                    "score": float(distances[0][i]),
                    "chunk": self.metadata[idx]["text"],
                    "source_id": self.metadata[idx]["source_id"]
                })
        return results

faiss_manager = FAISSManager()
