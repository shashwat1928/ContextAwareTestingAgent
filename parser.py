import os
import re
import json

class MultiLangParser:
    def __init__(self):
        self.supported_extensions = [".py", ".js", ".jsx", ".ts", ".tsx", ".java"]

    def _is_supported_file(self, file_path):
        return any(file_path.endswith(ext) for ext in self.supported_extensions)

    def extract_function_names(self, content, ext):
        function_names = []

        if ext == ".py":
            matches = re.findall(r"def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", content)
            function_names.extend(matches)

        elif ext in [".js", ".jsx", ".ts", ".tsx"]:
            matches = re.findall(r"function\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", content)
            function_names.extend(matches)

            matches = re.findall(r"(?:const|let|var)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(?:async\s*)?\(?[^\)]*\)?\s*=>", content)
            function_names.extend(matches)

            matches = re.findall(r"export\s+default\s+function\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", content)
            function_names.extend(matches)

        elif ext == ".java":
            matches = re.findall(r"(?:public|private|protected)?\s*(?:static)?\s*\w+\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", content)
            function_names.extend(matches)

        return function_names

    def parse_file(self, filepath):
        functions = []
        try:
            ext = os.path.splitext(filepath)[-1]
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                functions = self.extract_function_names(content, ext)
        except Exception as e:
            print(f"⚠️ Failed to parse {filepath}: {e}")
        return {"file": filepath, "functions": functions}

    def parse_repo(self, repo_path, specific_files=None):
        print(f"🔍 Parsing files in: {repo_path}")
        parsed_data = []

        specific_files = [os.path.normpath(os.path.join(repo_path, f)) for f in specific_files] if specific_files else None

        for root, _, files in os.walk(repo_path):
            for file in files:
                file_path = os.path.join(root, file)
                if not self._is_supported_file(file_path):
                    continue

                if specific_files is None or os.path.normpath(file_path) in specific_files:
                    parsed_result = self.parse_file(file_path)
                    if parsed_result["functions"]:
                        parsed_data.append(parsed_result)

        output_path = os.path.join(repo_path, "parsed_output.json")
        with open(output_path, "w") as f:
            json.dump(parsed_data, f, indent=2)

        print("✅ Parsing complete.")
        return parsed_data
