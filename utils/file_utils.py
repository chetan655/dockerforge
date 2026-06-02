import os
from typing import Any

from utils.logger import logger

IGNORE_DIRS = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache", "dist", "build", ".claude", ".cursor", ".idea", "*.log", ".env", ".env.example"}
IGNORE_FILES = {".DS_Store", "Thumbs.db", "*.swp", "*.swo", "*.bak", "*.pyc", "*.pyo", "*.pyd", "dockerforge.log", "*.log"}

def generate_file_tree(start_dir: str, current_dir: str = "", depth: int = 0, max_depth: int = 3) -> list[str]:
    """Recursively builds a tree representation of the codebase."""

    if depth > max_depth:
        return []

    tree = []
    full_path = os.path.join(start_dir, current_dir) if current_dir else start_dir

    try:
        items = sorted(os.listdir(full_path))
    except Exception as e:
        logger.warning(f"Failded to list dir {full_path}: {e}")
        return []

    for item in items:
        if item in IGNORE_DIRS or item in IGNORE_FILES:
            continue

        rel_item_path = os.path.join(current_dir, item) if current_dir else item
        item_full_path = os.path.join(start_dir, rel_item_path)

        indent = "  " * depth
        if os.path.isdir(item_full_path):
            tree.append(f"{indent} {item}")
            tree.extend(generate_file_tree(start_dir, rel_item_path, depth + 1, max_depth))
        else:
            tree.append(f"{indent} {item}")
    
    return tree

def detect_languages_and_configs(dir_path: str) -> dict[str, Any]:
    """Detect likely programming languages and setup configs in repo."""

    detected = {
        "languages": [],
        "config_files": [],
        "possible_entrypoints": []
    }

    # common config files for diff stacks
    config_mappings = {
        "package.json": "Node.js",
        "requirements.txt": "Python (pip)", 
        "pyproject.toml": "Python (poetry/uv/pep621)",
        "setup.py": "Python (setuptools)",
        "Pipfile": "Python (pipenv)",
        "go.mod": "Go", 
        "pom.xml": "Java (Maven)",
        "Build.grade": "Java (Gradle)",
        "Cargo.toml": "Rust",
        "Gemfile": "Ruby (bundler)",
        "composer.json": "PHP",
        "Dockerfile": "Docker",
        "docker-compose.yml": "Docker Compose",
    }


    entrypoint_names = {
        "main.py", "app.py", "wsgi.py", "server.js", "app.js", "index.js", "main.go", "main.rs"
    }  # to extend later

    for root, dirs, files in os.walk(dir_path):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

        for file in files:
            if file in config_mappings:
                lang = config_mappings[file]
                if lang not in detected["languages"]:
                    detected["languages"].append(lang)
                rel_path = os.path.relpath(os.path.join(root, file), dir_path)
                detected["config_files"].append(rel_path)

            if file in entrypoint_names:
                rel_path = os.path.relpath(os.path.join(root, file), dir_path)

                detected["possible_entrypoints"].append(rel_path)

    return detected


def read_key_file(repo_dir: str, filename: str) -> str:
    """Read the content of a confif file to give the LLM context on dependencies."""

    file_path = os.path.join(repo_dir, filename)
    if not os.path.exists(file_path):
        return ""

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f: 
            content = f.read(8192)  # cap at 8KB

            if len(content) == 8192:
                content += "\n... [Truncated due to size]"

            return content

    except Exception as e:
        logger.error(f"Error reading key file {filename}: {e}")
        return f"Error reading file: {str(e)}"

# testing

# if __name__ == "__main__":
#     test_path = os.path.abspath(".tmp_repos/HealthCare_agentic_chatbot")

#     print("Generating File Tree...")
#     tree = generate_file_tree(test_path)
#     print("\n".join(tree))

#     print("--------lang and config detection------------")
#     analysis = detect_languages_and_configs(test_path)
#     print(f"Analysis: {analysis}")

#     if analysis["config_files"]:
#         first_config = analysis["config_files"][2]
#         print("-----------reading key config file-----------")
#         print(read_key_file(test_path, first_config)[:500])
#     else:
#         print("no config files ")


    