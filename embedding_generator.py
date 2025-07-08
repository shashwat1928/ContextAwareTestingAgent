import os
import json
from sentence_transformers import SentenceTransformer

class EmbeddingGenerator:
    def __init__(self, parsed_path, output_path):
        self.parsed_path = parsed_path
        self.output_path = output_path
        self.model = SentenceTransformer('all-MiniLM-L6-v2')

    def load_parsed_data(self):
        if not os.path.exists(self.parsed_path):
            raise FileNotFoundError(f"❌ Parsed file not found at {self.parsed_path}")
        with open(self.parsed_path, "r") as f:
            return json.load(f)

    def generate_embedding(self, text):
        return self.model.encode(text).tolist()

    def generate_embeddings(self, parsed_data):
        results = []
        for item in parsed_data:
            file_path = item.get("file")
            functions = item.get("functions", [])
            for func in functions:
                if not func.strip():
                    continue
                embedding = self.generate_embedding(func)
                results.append({
                    "file_path": file_path,
                    "symbol": func,
                    "embedding": embedding
                })
        return results

    def save_embeddings(self, embeddings):
        with open(self.output_path, "w") as f:
            json.dump(embeddings, f, indent=2)

    def run(self):
        print(f"📥 Loading parsed data from: {self.parsed_path}")
        parsed_data = self.load_parsed_data()

        print("⚙️ Generating embeddings for parsed functions...")
        embeddings = self.generate_embeddings(parsed_data)

        print(f"💾 Saving {len(embeddings)} embeddings to: {self.output_path}")
        self.save_embeddings(embeddings)
