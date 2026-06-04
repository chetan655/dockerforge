import time
import docker
from typing import Any
from rich.console import Console

from utils.logger import logger

console = Console()

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
            image = client.images.get(tag)
            size_mb = image.attrs['Size'] / (1024 * 1024)
            logger.info(f"[green]Docker build succeeded for {tag} (Size: {size_mb:.2f}MB)[/green]")
            return True, "\n".join(logs)
        except docker.errors.ImageNotFound:
            logger.error(f"[red]Docker build failed for {tag}[/red]")
            return False, "\n".join(logs)
            
    except Exception as e:
        logger.error(f"Unexpected error during Docker build: {e}")
        return False, str(e)


        

# def run_and_verify_container(tag: str = "dockerforge-temp:latest", run_duration_sec: int = 5) -> tuple[bool, str]:
#     """Runs the build image in a container, waits for a few sec to verify it doesn't crash,
#     captures logs, and cleans up the container."""

#     client = docker.from_env()
#     container = None
#     logger.info(f"Running container from image: [cyan]{tag}[/cyan] to verify startup...")

#     try:
#         image = client.images.get(tag)
#         exposed_ports = image.attrs.get("Config", {}).get("ExposedPorts", {})

#         port_bindings = {}
#         if exposed_ports:
#             for port in exposed_ports:
#                 port_bindings[port] = ('127.0.0.1', 0)

#         container = client.containers.run(
#             tag, 
#             ports=port_bindings,
#             detach=True,
#             stdout=True,
#             stderr=True
#         )

#         time.sleep(run_duration_sec)

#         container.reload()
#         state = container.status
#         try:
#             logs = container.logs().decode("utf-8", errors="ignore")
#         except docker.errors.APIError as e:
#             if "configured logging driver does not support reading" in str(e):
#                 logs = "(Logs are unavailable because the host Docker logging driver does not support reading.)"
#             else:
#                 raise e

#         if state == "running" or container.attrs['State']['ExitCode'] == 0:
#             logger.info(f"[green]Container started successfully. Status: {state}[/green]")
#             return True, logs
#         else:
#             exit_code = container.attrs["State"]["ExitCode"]
#             logger.error(f"[red]Container exited with non-zero exit code: {exit_code}[/red]")
#             return False, logs
#     except docker.errors.NotFound:
#         logger.error(f"[red]Container not found for image: {tag}[/red]")
#         return False, f"Container not found for image: {tag}"
#     except docker.errors.APIError as e:
#         logger.error(f"[red]Error interacting with docker API: {e}[/red]")
#         return False, str(e)
#     except Exception as e:
#         logger.error(f"[red]Unexpected error running container: {e}[/red]")
#         return False, str(e)
    
#     finally:
#         if container:
#             try:
#                 logger.info("Clearning up verification container...")
#                 container.stop(timeout=2)
#                 container.remove()
#                 logger.info(f"[green]Cleanup completed.[/green]")
#             except Exception as e:
#                 logger.error(f"Error cleaning up container: {e}")


def run_and_verify_container(tag: str = "dockerforge-temp:latest", run_duration_sec: int = 5) -> tuple[bool, str]:
    """Runs the built image in a container, maps ports, checks if it responds to HTTP requests,
    captures logs, and cleans up the container."""
    import urllib.request
    import urllib.error

    client = docker.from_env()
    container = None
    logger.info(f"Running container from image: [cyan]{tag}[/cyan] to verify startup...")

    try:
        # 1. Fetch exposed ports from image metadata
        image = client.images.get(tag)
        exposed_ports = image.attrs.get("Config", {}).get("ExposedPorts", {})
        
        port_bindings = {}
        if exposed_ports:
            for port in exposed_ports:
                # Bind exposed ports to a random free port on localhost (127.0.0.1:0)
                port_bindings[port] = ('127.0.0.1', 0)

        # 2. Run the container with port bindings
        container = client.containers.run(
            tag, 
            detach=True,
            ports=port_bindings,
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

        # Check if it crashed
        if state != "running" and container.attrs['State']['ExitCode'] != 0:
            exit_code = container.attrs["State"]["ExitCode"]
            logger.error(f"[red]Container exited with non-zero exit code: {exit_code}[/red]")
            return False, logs

        # 3. Verify HTTP response if ports are exposed
        response_verified = True
        response_msg = ""
        
        if port_bindings:
            container_ports = container.attrs['NetworkSettings']['Ports']
            for container_port, host_bindings in container_ports.items():
                if host_bindings:
                    host_ip = host_bindings[0]['HostIp']
                    ip = '127.0.0.1' if host_ip == '0.0.0.0' else host_ip
                    host_port = host_bindings[0]['HostPort']
                    url = f"http://{ip}:{host_port}/"
                    
                    logger.info(f"Verifying container response by sending GET request to: {url}...")
                    try:
                        # Send HTTP request with a 2-second timeout
                        with urllib.request.urlopen(url, timeout=2) as response:
                            status_code = response.getcode()
                            response_msg = f"SUCCESS: Received HTTP response status {status_code} from {url}"
                            logger.info(f"[green]{response_msg}[/green]")
                    except urllib.error.HTTPError as e:
                        # Any valid HTTP status code (even 404/500) proves the server responded
                        response_msg = f"SUCCESS: Received HTTP response status {e.code} from {url}"
                        logger.info(f"[green]{response_msg}[/green]")
                    except Exception as e:
                        response_verified = False
                        response_msg = f"FAILURE: Container did not respond on {url}. Error: {str(e)}"
                        logger.error(f"[red]{response_msg}[/red]")
                        break

        if not response_verified:
            return False, f"Container started but did not respond: {response_msg}\nLogs:\n{logs}"

        return True, logs + (f"\n\nHTTP Verification:\n{response_msg}" if response_msg else "")

    except Exception as e:
        logger.error(f"[red]Unexpected error running container: {e}[/red]")
        return False, str(e)
    
    finally:
        if container:
            try:
                console.print("[cyan]]🤖 Cleaning up verification container...[/cyan]")
                container.stop(timeout=2)
                container.remove()
                console.print("[green]✔ Container cleaned up successfully.[/green]")
            except Exception as e:
                logger.error(f"Error cleaning up container: {e}")
