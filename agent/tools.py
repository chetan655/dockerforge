import os

from langchain_core.tools import tool

from utils.file_utils import generate_file_tree, detect_languages_and_configs, read_key_file
from utils.logger import logger

_build_attempts = {}

@tool
def analyze_repo(repo_path: str) -> str:
    """Analyzes the repository at the given path.
    
    Args:
        repo_path (str): The absolute local path to the cloned repository.
    """

    logger.info(f"Tool [cyan] analyze_repo[/cyan] called for {repo_path}")

    if not os.path.exists(repo_path):
        return f"Error: Repository path `{repo_path}` does not exist."

    tree = generate_file_tree(repo_path)
    tree_str = "\n".join(tree)

    analysis = detect_languages_and_configs(repo_path)
    
    config_contents = []
    for config_file in analysis.get("config_files", []):
        content = read_key_file(repo_path, config_file)
        if content:
            config_contents.append(f"--- Content of {config_file} ---\n{content}")

    configs_str = "\n\n".join(config_contents)

    result = f"""
    Codebase Analysis Report:
    =====================
    Detected Languages: {', '.join(analysis.get("languages", []))}
    Possible Entrypoints: {', '.join(analysis.get("possible_entrypoints", []))}
    Cofiguration Files Found: {', '.join(analysis.get('config_files', []))}
    
    File Tree:
    ----------
    {tree_str}
    
    Key Configurations:
    -----------------
    {configs_str}
    """

    return result

@tool
def read_file_content(repo_path: str, rel_path: str) -> str:
    """Reads the content of a specific file in the repository.
    
    Args:
        repo_path (str): The absolute local path to the cloned repository.
        rel_path (str): The relative path of the file from the repository root (e.g., 'package.json').
    """

    logger.info(f"Tool [cyan]read_file_content[/cyan] called for: {rel_path}")

    repo_abs = os.path.abspath(repo_path)
    full_path = os.path.abspath(os.path.join(repo_abs, rel_path))

    if not full_path.startswith(repo_abs):
        return f"Error: Access denied. You cannot read files outside the repository root."

    if not os.path.exists(full_path):
        return f"Error: File not found: {rel_path}"
    
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read(8192)
            if len(content) == 8192:
                content += "\n... [Truncated due to size]..."
            
            return content

    except Exception as e:
        return f"Error reading file `{rel_path}`: {str(e)}"


@tool
def write_dockerfile_to_disk(repo_path: str, content: str) -> str:
    """Writes the generated Dockerfile content to the root of the repository.
    
    Args:
        repo_path (str): The absolute local path to the cloned repository.
        content (str): The complete string content of the Dockerfile to write.
    """

    logger.info(f"Tool [cyan]write_dockerfile_to_disk[/cyan] called for: {repo_path}")

    dockerfile_path = os.path.join(repo_path, "Dockerfile")

    try:
        with open(dockerfile_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"[green]Successfully wrote Dockerfile to {dockerfile_path}[/green]")
        return f"Successfully wrote Dockerfile to {dockerfile_path}"
    
    except Exception as e:
        logger.error(f"Failed to write dockerfile: {e}")
        return f"Error writing Dockerfile: {str(e)}"

@tool
def build_docker_image_tool(repo_path: str, tag: str = "dockerforge-temp:latest") -> str:
    """Builds the Dockerfile located in the root of the repository path.
    
    Args:
        repo_path (str): The absolute local path to the cloned repository.
        tag (str): The Docker image tag to assign to the built image. Defaults to 'dockerforge-temp:latest'.
    """

    from utils.docker_utils import build_docker_image

    logger.info(f"Tool [cyan]build_docker_image_tool[/cyan] called.")

    attempts = _build_attempts.get(repo_path, 0)
    if attempts >= 3:
        logger.warning("Max build attempts (3) reached. Blocking further builds.")
        return "Error: You have already attempted to build this Dockerfile 3 times and failed. You must stop attempting to build and report the latest compilation error to the user."

    _build_attempts[repo_path] = attempts + 1
    logger.info(f"Build attempt {attempts+1} of 3 for {repo_path}")

    success, logs = build_docker_image(repo_path, tag)

    if success:
        return f"SUCCESS: Docker image built successfully. Tag: {tag}\nBuild Logs:\n{logs}"
    else:
        return f"FAILURE: Docker build failed. You must analyze these logs and fix the Dockerfile:\n{logs}"

@tool
def verify_container_tool(tag: str = "dockerforge-temp:latest") -> str:
    """Runs the built container to verify if it starts correctly.
    
    Args:
        tag (str): The Docker image tag to run. Defaults to 'dockerforge-temp:latest'.
    """

    from utils.docker_utils import run_and_verify_container
    
    logger.info(f"Tool [cyan]verify_container_tool[/cyan] called.")

    success, logs = run_and_verify_container(tag, run_duration_sec=5)

    if success:
        return f"SUCCESS: Container started and is running fine. Startup Logs:\n{logs}"
    else:
        return f"FAILURE: Container crashed or failed on startup. Analyze these logs to fix the Dockerfile or startup command:\n{logs}"

