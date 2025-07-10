import os
import json
import tempfile
from git import Repo
from litellm import embedding
import faiss

class GitDiffAnalyzer:
    def __init__(self, repo_url, clone_path="cloned_repo"):
        self.repo_url = repo_url
        self.clone_path = clone_path

    def clone_or_pull_repo(self):
        if not os.path.exists(self.clone_path):
            print("📥 Cloning repo...")
            Repo.clone_from(self.repo_url, self.clone_path)
        else:
            print("🔄 Pulling latest changes...")
            repo = Repo(self.clone_path)
            repo.remotes.origin.pull()

    def get_changed_files(self):
        repo = Repo(self.clone_path)
        commits = list(repo.iter_commits("main", max_count=2))  # adjust branch name if needed
        if len(commits) < 2:
            return []

        diff_index = commits[0].diff(commits[1])
        changed = [item.a_path for item in diff_index if item.a_path.endswith(".py")]
        return list(set(changed))

class FunctionParser:
    def extract_functions(self, file_path):
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            import re
            matches = re.findall(r"def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", content)
            return matches
        except Exception as e:
            print(f"❌ Failed to parse {file_path}: {e}")
            return []

class EmbeddingStore:
    def __init__(self, vector_store_path="faiss.index", metadata_path="metadata.json"):
        self.index = faiss.IndexFlatL2(384)  # 384 dims for text-embedding-3-small
        self.metadata = []
        self.vector_store_path = vector_store_path
        self.metadata_path = metadata_path

    def generate_embedding(self, text):
        try:
            response = embedding(
                model="text-embedding-3-small", 
                input=text
            )
            return response["data"][0]["embedding"]
        except Exception as e:
            print(f"❌ Failed to embed text: {text[:30]}... | Error: {e}")
            return None

    def add(self, file_path, function_name, vector):
        self.index.add([vector])
        self.metadata.append({
            "file": file_path,
            "function": function_name
        })

    def save(self):
        faiss.write_index(self.index, self.vector_store_path)
        with open(self.metadata_path, "w") as f:
            json.dump(self.metadata, f, indent=2)
        print(f"✅ Stored {len(self.metadata)} embeddings in FAISS and metadata.json")

def main():
    repo_url = "https://github.com/pydantic/pydantic"  # replace with your repo
    analyzer = GitDiffAnalyzer(repo_url)
    analyzer.clone_or_pull_repo()

    changed_files = analyzer.get_changed_files()
    print("📝 Changed files:", changed_files)
    if not changed_files:
        print("⚠️ No changed files to process.")
        return

    parser = FunctionParser()
    store = EmbeddingStore()

    for rel_path in changed_files:
        full_path = os.path.join(analyzer.clone_path, rel_path)
        function_names = parser.extract_functions(full_path)
        print(f"🔍 {rel_path}: {len(function_names)} functions")

        for fn in function_names:
            vector = store.generate_embedding(fn)
            if vector:
                store.add(rel_path, fn, vector)

    store.save()

if __name__ == "__main__":
    main()
    
