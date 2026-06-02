import os
import shutil
import git
from urllib.parse import urlparse

from utils.logger import logger

def clone_repo(repo_url: str, base_tmp_dir: str = ".tmp_repos") -> str:
    """Clone a public github repo to a local temporary dir."""

    repo_url = repo_url.strip()
    if not repo_url.startswith(("http://", "https://", "git@")):
        raise ValueError(f"Invalid repo url: {repo_url}")

    path_parts = urlparse(repo_url).path.strip("/").split("/")

    if len(path_parts) != 2:
        raise ValueError(f"Invalid repo url: {repo_url}")
    repo_owner, repo_name = path_parts

    if repo_name.endswith(".git"):
        repo_name = repo_name[:-4]

    os.makedirs(base_tmp_dir, exist_ok=True)
    target_dir = os.path.abspath(os.path.join(base_tmp_dir, repo_name))

    if os.path.exists(target_dir):
        logger.info(f"Removing existing directory: {target_dir}")
        shutil.rmtree(target_dir)

    try:
        logger.info(f"Cloning [cyan]{repo_url}[/cyan] into [yellow]{target_dir}[/yellow]...")
        git.Repo.clone_from(repo_url, target_dir, depth=1)
        logger.info(f"[green]Successfully cloned {repo_url} into {target_dir}[/green]")
        return target_dir
    except Exception as e:
        shutil.rmtree(target_dir, ignore_errors=True)
        logger.error(f"Failed to clone repo [red]{repo_url}[/red]")
        raise Exception(f"Failed to clone repo {repo_url}") from e

# clone_repo("https://github.com/chetan655/HealthCare_agentic_chatbot")