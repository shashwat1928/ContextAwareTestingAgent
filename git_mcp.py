import os
import shutil
import subprocess
import git
from git import Repo
import sys




# Add project root directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.parser import MultiLangParser  # ✅ Now this will work correctly


class GitMCP:
    def __init__(self, repo_url, local_path="cloned_repo"):
        self.repo_url = repo_url
        self.local_path = local_path

    def clone_repo(self):
        if os.path.exists(self.local_path):
            shutil.rmtree(self.local_path)
        self.repo = git.Repo.clone_from(self.repo_url, self.local_path)
        print("✅ Repository cloned.")

    def get_changed_files(self):
        commits = list(self.repo.iter_commits('main', max_count=2))
        if len(commits) < 2:
            print("❌ Not enough commits to compare.")
            return []

        diff_index = commits[0].diff(commits[1])
        changed_files = [
            item.a_path for item in diff_index if item.change_type in ['A', 'M']
        ]
        return changed_files

    def run(self):
        self.clone_repo()
        changed_files = self.get_changed_files()
        if not changed_files:
            print("⚠️ No changed files to parse.")
            return

        print("🔍 Changed files:", changed_files)

        # Parse only the changed files
        parser = MultiLangParser()
        changed_paths = [os.path.join(self.local_path, f) for f in changed_files]
        result = parser.parse_repo(self.local_path, specific_files=changed_paths)
        print("✅ Parsing complete.")
        return result

if __name__ == "__main__":
    repo_url = "https://github.com/pydantic/pydantic"  # Replace this
    mcp = GitMCP(repo_url)
    mcp.run()
