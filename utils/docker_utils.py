import time
import docker
from typing import Any

from utils.logger import logger

# def build_docker_image(repo_dir: str, tag: str = "dockerforge-temp:latest") -> tuple[bool, str]:
#     """Builds a docker image in the specified dir.
    
#     Returns:
#         (boo, str): (True, 'Success msg') if build succeeds
#         (False, 'error msg') on failure
#     """

#     client = docker.from_env()
#     logger.info(f"Starting docker build with tag: [cyan]{tag}[/cyan]")

#     try:
#         image, build_logs = client.images.build(
#             path=repo_dir,
#             tag=tag,
#             rm=True,
#             forcerm=True
#         )

#         logs = []
#         for log in build_logs:
#             if "stream" in log:
#                 logs.append(log["stream"].strip())

#         logger.info(f"[green]Docker build successfully: {tag}[/green]")
#         return True, "\n".join(logs)
    
#     except docker.errors.BuildError as e:
#         error_log = []
#         for log in e.build_log:
#             if "stream" in log:
#                 error_log.append(log["stream"].strip())
#             elif "error" in log:
#                 error_log.append(log["error"].strip())

#         error_msg = "\n".join(error_log)
#         logger.error(f"[red]Docker build failed for {tag}[/red]")
#         return False, error_msg

#     except Exception as e:
#         logger.error(f"Unexpected error during build: {e}")
#         return False, str(e)


def build_docker_image(repo_dir: str, tag: str = "dockerforge-temp:latest") -> tuple[bool, str]:
    """
    Builds a Docker image in the specified directory and streams the compilation logs
    live to the terminal in real-time.
    
    Returns:
        (bool, str): (True, "Success message") if build succeeds, 
                     (False, "Error log") if build fails.
    """
    client = docker.from_env()

    try:
        client.images.remove(image=tag, force=True)
        logger.info(f"Removed old image: {tag} before build.")
    except Exception as e:
        pass

    logger.info(f"Starting Docker build with tag: [cyan]{tag}[/cyan]...")
    
    try:
        log_generator = client.api.build(
            path=repo_dir,
            tag=tag,
            rm=True,          
            forcerm=True,     
            decode=True      
        )
        
        logs = []
        has_error = False

        for chunk in log_generator:
            if 'stream' in chunk:
                line = chunk['stream'].strip()
                if line:
                    # print(f"  [dim]{line}[/dim]", flush=True)
                    logs.append(line)
            # Check for build errors
            elif 'error' in chunk:
                error_line = chunk['error'].strip()
                print(f"  [bold red]✖ {error_line}[/bold red]", flush=True)
                logs.append(error_line)
                has_error = True
                
        if has_error:
            logger.error(f"[red]Docker build failed for {tag}[/red]")
            return False, "\n".join(logs)

        try:
            client.images.get(tag)
            logger.info(f"[green]Docker build succeeded for {tag}[/green]")
            return True, "\n".join(logs)
        except docker.errors.ImageNotFound:
            logger.error(f"[red]Docker build failed for {tag}[/red]")
            return False, "\n".join(logs)
            
    except Exception as e:
        logger.error(f"Unexpected error during Docker build: {e}")
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
        try:
            logs = container.logs().decode("utf-8", errors="ignore")
        except docker.errors.APIError as e:
            if "configured logging driver does not support reading" in str(e):
                logs = "(Logs are unavailable because the host Docker logging driver does not support reading.)"
            else:
                raise e

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

