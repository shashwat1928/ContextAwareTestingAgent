import os
import json
import re
from neo4j import GraphDatabase

class DependencyGraphBuilder:
    def __init__(self, uri="neo4j://127.0.0.1:7687", user="neo4j", password="Shashwat@2000"):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def create_function_node(self, tx, file_path, function_name):
        tx.run("MERGE (f:Function {name: $name, file: $file})", name=function_name, file=file_path)

    def create_dependency(self, tx, caller, callee):
        tx.run(
            """
            MATCH (a:Function {name: $caller})
            MATCH (b:Function {name: $callee})
            MERGE (a)-[:DEPENDS_ON]->(b)
            """, caller=caller, callee=callee
        )

    def add_function_nodes_and_dependencies(self, repo_path, changed_files):
        parsed_path = os.path.join(repo_path, "parsed_output.json")
        print(f"🔍 Looking for: {parsed_path}")

        if not os.path.exists(parsed_path):
            print("❌ parsed_output.json not found.")
            return

        with open(parsed_path, "r") as f:
            data = json.load(f)

        changed_file_paths = {os.path.join(repo_path, f['file'] if isinstance(f, dict) else f) for f in changed_files}

        with self.driver.session() as session:
            for file_data in data:
                file_path = file_data["file"]
                full_path = os.path.abspath(file_path)

                if full_path not in changed_file_paths:
                    continue

                functions = file_data["functions"]
                print(f"📌 Processing: {file_path} ({len(functions)} functions)")

                for func in functions:
                    session.execute_write(self.create_function_node, file_path, func)

                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()

                    for caller in functions:
                        for callee in functions:
                            if caller != callee and re.search(rf"\b{re.escape(callee)}\b", content):
                                print(f"🔗 {caller} depends on {callee}")
                                session.execute_write(self.create_dependency, caller, callee)
                except Exception as e:
                    print(f"⚠️ Could not read {file_path}: {e}")

        print("✅ Dependency graph created for changed files.")

