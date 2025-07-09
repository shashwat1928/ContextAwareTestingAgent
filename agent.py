import os
import javalang
import networkx as nx
from git import Repo

# -----------------------------
# Git Utilities
# -----------------------------
def clone_repo(url, repo_dir):
    if not os.path.exists(repo_dir):
        print(f"Cloning {url}...")
        Repo.clone_from(url, repo_dir)
    return Repo(repo_dir)

def get_last_two_commits(repo):
    branch = 'master'
    commits = list(repo.iter_commits(branch, max_count=2))
    return commits[1], commits[0]

def get_changed_java_files(repo, old_commit, new_commit):
    diff = new_commit.diff(old_commit)
    return [d.a_path for d in diff if d.a_path.endswith('.java')]

# -----------------------------
# Java Parser using javalang
# -----------------------------
def extract_java_entities(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()

        tree = javalang.parse.parse(code)
        entities = []

        for path, node in tree:
            if isinstance(node, javalang.tree.ClassDeclaration):
                class_name = node.name
                entities.append(class_name)
            elif isinstance(node, javalang.tree.MethodDeclaration):
                class_context = path[-2].name if len(path) >= 2 and isinstance(path[-2], javalang.tree.ClassDeclaration) else ""
                full_method = f"{class_context}.{node.name}" if class_context else node.name
                entities.append(full_method)

        return entities
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        return []

def extract_method_calls(method_node):
    calls = []

    def walk(node):
        if isinstance(node, javalang.tree.MethodInvocation):
            calls.append(node.member)
        for child in node.children:
            if isinstance(child, list):
                for item in child:
                    if isinstance(item, javalang.tree.Node):
                        walk(item)
            elif isinstance(child, javalang.tree.Node):
                walk(child)

    walk(method_node)
    return calls

# -----------------------------
# Dependency Graph Builder
# -----------------------------
def build_dependency_graph(file_paths):
    graph = nx.DiGraph()

    all_defs = {}  # map: method name → file path

    for path in file_paths:
        defs = extract_java_entities(path)
        for d in defs:
            graph.add_node(d, file=path)
            all_defs[d] = path
            # Co-located edges
            for other in defs:
                if d != other:
                    graph.add_edge(d, other, reason="co-located")

    # Add call relationships
    for path in file_paths:
        with open(path, "r", encoding="utf-8") as f:
            code = f.read()
        try:
            tree = javalang.parse.parse(code)
            for _, node in tree.filter(javalang.tree.MethodDeclaration):
                method_name = node.name
                class_name = None
                for ancestor in _:
                    if isinstance(ancestor, javalang.tree.ClassDeclaration):
                        class_name = ancestor.name
                        break
                full_name = f"{class_name}.{method_name}" if class_name else method_name

                if hasattr(node, "body") and node.body:
                    calls = extract_method_calls(node)
                    for call in calls:
                        for defined in all_defs:
                            if defined.endswith(call):  # basic fuzzy match
                                graph.add_edge(full_name, defined, reason="calls")
        except Exception as e:
            print(f"Call analysis failed for {path}: {e}")

    return graph


# -----------------------------
# Knowledge Graph Query
# -----------------------------
def get_affected_entities(graph, changed_files):
    affected = set()
    changed_files = [os.path.abspath(f) for f in changed_files]

    for node, data in graph.nodes(data=True):
        if os.path.abspath(data.get("file", "")) in changed_files:
            affected.add(node)
    return affected

def expand_dependencies(graph, entities):
    expanded = set(entities)
    for e in entities:
        if e in graph:
            expanded.update(graph.successors(e))
            expanded.update(graph.predecessors(e))
    return expanded

# -----------------------------
# Main
# -----------------------------
def main():
    REPO_URL = "https://github.com/houarizegai/calculator.git"
    REPO_DIR = "./calculator"

    repo = clone_repo(REPO_URL, REPO_DIR)
    old_commit, new_commit = get_last_two_commits(repo)

    changed_rel = get_changed_java_files(repo, old_commit, new_commit)
    changed_abs = [os.path.abspath(os.path.join(REPO_DIR, f)) for f in changed_rel]

    print("\n🔧 Changed Java Files:")
    for f in changed_rel:
        print(" -", f)

    all_java_files = []
    for root, _, files in os.walk(REPO_DIR):
        for file in files:
            if file.endswith(".java"):
                all_java_files.append(os.path.join(root, file))

    graph = build_dependency_graph(all_java_files)
    # nx.write_gpickle(graph, "dep_graph.gpickle")
    # print("✅ Graph saved to dep_graph.gpickle")

    affected = get_affected_entities(graph, changed_abs)
    impacted = expand_dependencies(graph, affected)

    print("\n📌 Affected Entities:")
    for a in affected:
        print(" -", a)

    print("\n📌 Impacted Entities (Affected + Related):")
    for i in impacted:
        print(" -", i)

if __name__ == "__main__":
    main()
