import os
import pickle
import networkx as nx
import javalang
from git import Repo
from langchain.agents import initialize_agent, Tool
from langchain_community.chat_models import ChatOpenAI
from langchain.tools import tool

# ---------------------- PART 1: BUILD GRAPH FROM JAVA GIT REPO ----------------------

REPO_URL = "https://github.com/houarizegai/calculator.git"
REPO_DIR = "./calculator"
GRAPH_PATH = "dep_graph.gpickle"
IMPACTED_PATH = "impacted.pkl"

def clone_repo(url, repo_dir):
    if not os.path.exists(repo_dir):
        Repo.clone_from(url, repo_dir)
    return Repo(repo_dir)

def get_last_two_commits(repo):
    branch = 'main' if 'main' in repo.heads else 'master'
    commits = list(repo.iter_commits(branch, max_count=2))
    return commits[1], commits[0]

def get_changed_java_files(repo, old_commit, new_commit):
    diff = new_commit.diff(old_commit)
    return [d.a_path for d in diff if d.a_path.endswith('.java')]

def extract_java_entities(file_path):
    entities = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        tree = javalang.parse.parse(code)
        for path, node in tree:
            if isinstance(node, javalang.tree.ClassDeclaration):
                entities.append(node.name)
            elif isinstance(node, javalang.tree.MethodDeclaration):
                cls = next((p.name for p in path if isinstance(p, javalang.tree.ClassDeclaration)), "")
                entities.append(f"{cls}.{node.name}" if cls else node.name)
    except Exception as e:
        print(f"Error in {file_path}: {e}")
    return entities

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

def build_dependency_graph(file_paths):
    graph = nx.DiGraph()
    all_defs = {}
    for path in file_paths:
        defs = extract_java_entities(path)
        for d in defs:
            graph.add_node(d, file=path)
            all_defs[d] = path
            for other in defs:
                if d != other:
                    graph.add_edge(d, other, reason="co-located")
    for path in file_paths:
        with open(path, "r", encoding="utf-8") as f:
            code = f.read()
        try:
            tree = javalang.parse.parse(code)
            for _, node in tree.filter(javalang.tree.MethodDeclaration):
                cls = next((p.name for p in _ if isinstance(p, javalang.tree.ClassDeclaration)), "")
                full_name = f"{cls}.{node.name}" if cls else node.name
                if hasattr(node, "body") and node.body:
                    calls = extract_method_calls(node)
                    for call in calls:
                        for defined in all_defs:
                            if defined.endswith(call):
                                graph.add_edge(full_name, defined, reason="calls")
        except Exception as e:
            print(f"Call analysis failed in {path}: {e}")
    return graph

def get_affected_entities(graph, changed_files):
    affected = set()
    changed_files = [os.path.abspath(f) for f in changed_files]
    for node, data in graph.nodes(data=True):
        if os.path.abspath(data.get("file", "")) in changed_files:
            affected.add(node)
    return affected

def expand_dependencies(graph, entities):
    impacted = set(entities)
    for e in entities:
        if e in graph:
            impacted.update(graph.successors(e))
            impacted.update(graph.predecessors(e))
    return impacted

def build_and_save_graph():
    repo = clone_repo(REPO_URL, REPO_DIR)
    old, new = get_last_two_commits(repo)
    changed = get_changed_java_files(repo, old, new)
    abs_changed = [os.path.abspath(os.path.join(REPO_DIR, f)) for f in changed]

    all_java = [os.path.join(r, f) for r, _, files in os.walk(REPO_DIR) for f in files if f.endswith(".java")]
    graph = build_dependency_graph(all_java)

    affected = get_affected_entities(graph, abs_changed)
    impacted = expand_dependencies(graph, affected)

    with open(GRAPH_PATH, "wb") as f:
        pickle.dump(graph, f)

    with open(IMPACTED_PATH, "wb") as f:
        pickle.dump(impacted, f)
    print("✅ Graph and impacted entities saved.")

# ---------------------- PART 2: LANGCHAIN QUERY AGENT ----------------------
def impacted_code_tool(_: str = "") -> str:
    """Returns impacted entities (methods/classes) from the dependency graph."""
    with open(GRAPH_PATH, "rb") as f:
        graph = pickle.load(f)

    impacted = [n for n, d in graph.nodes(data=True) if d.get("changed")]
    return ", ".join(impacted) if impacted else "No impacted entities found."

def run_agent():
    with open(GRAPH_PATH, "rb") as f:
        graph = pickle.load(f)

    with open(IMPACTED_PATH, "rb") as f:
        impacted_entities = pickle.load(f)

    def list_all_nodes():
        return list(graph.nodes())

    def get_impacted():
        return list(impacted_entities)

    def get_callers(entity):
        return list(graph.predecessors(entity))

    def get_callees(entity):
        return list(graph.successors(entity))

    def search_entity(name):
        return [n for n in graph.nodes() if name.lower() in n.lower()]

    tools = [
        Tool(name="ListNodes", func=lambda _: str(list_all_nodes()), description="List all classes and methods"),
        Tool.from_function(func=impacted_code_tool,name="impacted_code_tool",description="Get impacted methods/classes from the recent commit. Input can be anything.",),
        Tool(name="Callers", func=get_callers, description="Find who calls a given method"),
        Tool(name="Callees", func=get_callees, description="Find what a method calls"),
        Tool(name="Search", func=search_entity, description="Search for a function/class by partial name")
    ]

    llm = ChatOpenAI(
        openai_api_key="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",  # 🔑 Your OpenRouter key
        openai_api_base="https://openrouter.ai/api/v1",
        model="mistralai/mistral-7b-instruct",
        temperature=0.3
    )
    agent = initialize_agent(tools, llm, agent_type="zero-shot-react-description", verbose=True, handle_parsing_errors=True,)

    while True:
        query = input("\n🧠 Ask your code graph (or type 'exit'): ")
        if query.lower() in {"exit", "quit"}:
            break
        print(agent.invoke(query))

# ---------------------- ENTRY POINT ----------------------

if __name__ == "__main__":
    if not os.path.exists(GRAPH_PATH):
        build_and_save_graph()
    run_agent()
