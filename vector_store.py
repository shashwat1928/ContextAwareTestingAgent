import os
import json
import faiss
import numpy as np

class VectorStore:
    def __init__(self, embedding_path, index_path="faiss_index/faiss.index", metadata_path="faiss_index/metadata.json"):
        self.embedding_path = embedding_path
        self.index_path = index_path
        self.metadata_path = metadata_path
        self.index = None
        self.metadata = []

        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)

    def load_embeddings(self):
        with open(self.embedding_path, "r") as f:
            data = json.load(f)
        embeddings = [item["embedding"] for item in data]
        metadata = [{"file_path": item["file_path"], "symbol": item["symbol"]} for item in data]
        return np.array(embeddings).astype("float32"), metadata

    def build_faiss_index(self):
        if os.path.exists(self.index_path) and os.path.exists(self.metadata_path):
            print("📥 Loading FAISS index from disk...")
            self.load_index()
        else:
            print("⚙️ Building new FAISS index...")
            embeddings, self.metadata = self.load_embeddings()
            dimension = embeddings.shape[1]
            self.index = faiss.IndexFlatL2(dimension)
            self.index.add(embeddings)
            self.save_index()

    def save_index(self):
        faiss.write_index(self.index, self.index_path)
        with open(self.metadata_path, "w") as f:
            json.dump(self.metadata, f)
        print("✅ FAISS index and metadata saved.")

    def load_index(self):
        self.index = faiss.read_index(self.index_path)
        with open(self.metadata_path, "r") as f:
            self.metadata = json.load(f)

    def query(self, query_embedding, top_k=5):
        if self.index is None:
            raise ValueError("FAISS index not loaded.")
        query_vector = np.array([query_embedding]).astype("float32")
        distances, indices = self.index.search(query_vector, top_k)
        return [self.metadata[i] for i in indices[0] if i < len(self.metadata)]
