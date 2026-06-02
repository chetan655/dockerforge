import time
import docker
from typing import Any

from utils.logger import logger

def build_docker_image(repo_dir: str, tag: str = "dockerforge-temp:latest") -> tuple[bool, str]:
    """Builds a docker image in the specified dir.
    
    Returns:
        (boo, str): (True, 'Success msg') if build succeeds
        (False, 'error msg') on failure
    """

    client = docker.from_env()
    logger.info(f"Starting docker build with tag: [cyan]{tag}[/cyan]")

    try:
        image, build_logs = client.images.build(
            path=repo_dir,
            tag=tag,
            rm=True,
            forcerm=True
        )

        logs = []
        for log in build_logs:
            if "stream" in log:
                logs.append(log["stream"].strip())

        logger.info(f"[green]Docker build successfully: {tag}[/green]")
        return True, "\n".join(logs)
    
    except docker.errors.BuildError as e:
        error_log = []
        for log in e.build_log:
            if "stream" in log:
                error_log.append(log["stream"].strip())
            elif "error" in log:
                error_log.append(log["error"].strip())

        error_msg = "\n".join(error_log)
        logger.error(f"[red]Docker build failed for {tag}[/red]")
        return False, error_msg

    except Exception as e:
        logger.error(f"Unexpected error during build: {e}")
        return False, str(e)

        

def run_and_verify_container(tag: str = "dockerforge-temp:latest", run_duration_sec: int = 5) -> tuple[bool, str]:
    """Runs the build image in a container, waits for a few sec to verify it doesn't crash,
    captures logs, and cleans up the container."""

    client = docker.from_env()
    container = None
    logger.info(f"Running container from image: [cyan]{tag}[/cyan] to verify startup...")

    try:
        container = client.containers.run(
            tag, 
            detach=True,
            stdout=True,
            stderr=True
        )

        time.sleep(run_duration_sec)

        container.reload()
        state = container.status

        logs = container.logs().decode("utf-8", errors="ignore")

        if state == "running" or container.attrs['State']['ExitCode'] == 0:
            logger.info(f"[green]Container started successfully. Status: {state}[/green]")
            return True, logs
        else:
            exit_code = container.attrs["State"]["ExitCode"]
            logger.error(f"[red]Container exited with non-zero exit code: {exit_code}[/red]")
            return False, logs
    except docker.errors.NotFound:
        logger.error(f"[red]Container not found for image: {tag}[/red]")
        return False, f"Container not found for image: {tag}"
    except docker.errors.APIError as e:
        logger.error(f"[red]Error interacting with docker API: {e}[/red]")
        return False, str(e)
    except Exception as e:
        logger.error(f"[red]Unexpected error running container: {e}[/red]")
        return False, str(e)
    
    finally:
        if container:
            try:
                logger.info("Clearning up verification container...")
                container.stop(timeout=2)
                container.remove()
                logger.info(f"[green]Cleanup completed.[/green]")
            except Exception as e:
                logger.error(f"Error cleaning up container: {e}")

