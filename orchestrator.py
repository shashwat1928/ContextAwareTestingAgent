import os
from agent.git_mcp import GitMCP
from agent.parser import MultiLangParser
from agent.embedding_generator import EmbeddingGenerator
from agent.dependency_graph import DependencyGraphBuilder
from agent.vector_store import VectorStore

class orchestrator:
    def __init__(self, repo_url):
        self.repo_url = repo_url
        self.repo_path = "cloned_repo"
        self.parsed_output_path = os.path.join(self.repo_path, "parsed_output.json")
        self.embedding_output_path = "function_embeddings.json"
        self.neo4j_uri = "neo4j://localhost:7687"
        self.neo4j_user = "neo4j"
        self.neo4j_password = "Shashwat@2000"

    def run(self):
        print("🚀 Orchestrator started...")

        # Step 1: Clone repo + get changed files
        print("🔄 Cloning and diffing repo...")
        mcp = GitMCP(repo_url=self.repo_url, local_path=self.repo_path)
        changed_files = mcp.run()
        print(f"✅ Changed files: {changed_files}")

        # Step 2: Parse only changed files
        print("🧠 Parsing changed files...")
        parser = MultiLangParser()
        parser.parse_repo(self.repo_path, specific_files=changed_files)
        print("✅ Parsing complete")

        # Step 3: Generate Embeddings
        print("🧬 Generating embeddings...")
        generator = EmbeddingGenerator(parsed_path=self.parsed_output_path,
                                       output_path=self.embedding_output_path)
        generator.run()
        print("✅ Embeddings generated")

        print("💾 Building vector index...")
        vector_store = VectorStore("function_embeddings.json")
        vector_store.build_faiss_index()
        print("✅ Vector store index built.")


        # Step 4: Build Dependency Graph
        print("🕸️ Creating dependency graph in Neo4j...")
        graph = DependencyGraphBuilder(uri=self.neo4j_uri,
                                       user=self.neo4j_user,
                                       password=self.neo4j_password)
        graph.add_function_nodes_and_dependencies(self.repo_path, changed_files)
        print("✅ Dependency graph created")

        print("🎉 Orchestration complete!")

if __name__ == "__main__":
    repo_url = "https://github.com/pydantic/pydantic"
    orchestrator = orchestrator(repo_url)
    orchestrator.run()
