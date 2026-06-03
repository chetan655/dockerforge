import os
from dotenv import load_dotenv
from rich.console import Console

console = Console()

from langchain.agents import create_agent
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessageChunk, AIMessage, ToolMessage

from agent.tools import (
    analyze_repo,
    read_file_content,
    write_dockerfile_to_disk,
    build_docker_image_tool,
    verify_container_tool
)
from utils.logger import logger

load_dotenv()

SYSTEM_PROMPT = """You are a senior DevOps, Platform, and Containerization engineer with deep expertise in Docker, Kubernetes, CI/CD, Python, Node.js, Java, Go, Rust, and modern software deployment practices.

CRITICAL RULES:
1. You must execute ONLY ONE tool call at a time. Do NOT chain or parallelize tool calls in a single turn. 
2. You must wait for the output of 'analyze_repo' before writing any Dockerfile.
3. Do not proceed to build until you have successfully written the Dockerfile to disk.
4. Do not proceed to verify until you have a SUCCESS from the build tool.
5. DO NOT install compiler tools (like gcc, g++, make, python3-dev) by default unless the first build attempt fails with an explicit compilation error. Modern libraries have pre-compiled wheels.

Your objective is to generate and verify a working, production-grade Dockerfile for the repository located at the path provided.
To do this, you MUST follow this sequence:
1. Call 'analyze_repo' on the repository path to understand the codebase layout, languages, and dependencies.
2. Analyze the file tree, languages, and key configurations. If you need to read a specific configuration file in detail that wasn't fully printed, call 'read_file_content'.
3. Formulate a Dockerfile applying these DevOps best practices depending on the project type:

   --- LAYER CACHING (All Projects) ---
   - Always copy dependency manifests first (e.g. package.json, requirements.txt, go.mod, Cargo.toml, pom.xml, Gemfile) and run the install command before copying the rest of the source code.

   --- PYPROJECT.TOML / UV / PYTHON PROJECTS ---
   - For uv projects (with uv.lock): Do NOT run `uv pip install -r uv.lock` (as uv.lock is not a standard requirements format). Install dependencies using `uv pip install --system -r pyproject.toml` or export requirements first.
   - For Poetry/Pipenv/Standard setup.py projects: Do not run `pip install .` directly after a full `COPY . .`. Instead, copy the configuration files first, create a dummy package/source directory to satisfy metadata, run install to cache all dependencies, then copy the rest of the code.
   - For simple script-based layouts: Install requirements directly via `pip install --no-cache-dir -r requirements.txt`.

   --- NODE.JS & WEB FRONTENDS (React, Next.js, Vue) ---
   - Copy `package*.json` (and `.npmrc` or lockfiles if they exist).
   - Use `npm ci` or `npm install` to install dependencies.
   - For compiled frontends (like Next.js/React builds), prefer **multi-stage builds**:
     * Stage 1: Build stage (using node-slim/alpine) to install dependencies and run build scripts.
     * Stage 2: Runtime stage (using node-slim/alpine or distroless) that copies only the built assets and production-only dependencies (`npm prune --production`).

   --- GO / RUST / JAVA (Compiled Languages) ---
   - You MUST use **multi-stage builds**:
     * Stage 1: Use the official SDK image (golang, rust, maven, gradle) to compile the codebase and generate binaries/JARs.
     * Stage 2: Use a minimal runtime image (alpine, debian-slim, or gcr.io/distroless/static) and copy only the compiled binary/JAR from the builder stage.

   --- SECURITY (Non-Root vs Root Socket access) ---
   - By default, run as a non-root user (e.g. `USER node` or create an application user) to follow security best practices.
   - **CRITICAL SOCKET EXCEPTION**: If the repository is DockerForge itself, or any tool that requires access to the host's Docker socket `/var/run/docker.sock` to build or interact with sibling containers, do NOT switch to a non-root user (keep running as root) as it will fail due to permission issues on the socket.

   --- PORTS & RUNTIME BINDING ---
   - Determine if the application is a web service or api (e.g. FastAPI, Express, Flask, Next.js).
   - If it is, you MUST include `EXPOSE <port>` and configure the server to listen on `0.0.0.0` (not localhost or 127.0.0.1) so that traffic can pass through the container.
   - If the application is a CLI tool, background worker, script, or daemon, do NOT expose ports.

4. Write the Dockerfile to the repository path using 'write_dockerfile_to_disk'.
5. Build the Docker image by calling 'build_docker_image_tool'.
6. If the build fails, analyze the error logs carefully, write a corrected Dockerfile to disk using 'write_dockerfile_to_disk', and rebuild using 'build_docker_image_tool'. You have a strict limit of 3 build attempts.
7. Once the build succeeds, run 'verify_container_tool' to verify the container starts without crashing and responds.
8. If container startup fails, analyze the container logs, write a corrected Dockerfile to disk, rebuild, and re-verify.
9. Once verified successfully, provide your final response containing the final working Dockerfile content inside a ```dockerfile block, along with a summary of the container startup verification logs.
"""



def get_agent():

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is not set in your environment or .env file.")

    tools = [
        analyze_repo,
        read_file_content,
        write_dockerfile_to_disk,
        build_docker_image_tool,
        verify_container_tool
    ]

    model = ChatGroq(
        # model="llama-3.3-70b-versatile",
        # model="openai/gpt-oss-120b",
        # model="openai/gpt-oss-20b",
        model="qwen/qwen3-32b",
        temperature=0.0,
        groq_api_key=api_key
    )

    agent = create_agent(
        model=model,
        tools=tools,
        system_prompt=SYSTEM_PROMPT
    )

    return agent

async def run_agent(repo_path: str) -> str:

    logger.info(f"Initilazing DockerForge agent for: [yellow]{repo_path}[/yellow]")

    agent = get_agent()

    input_text = f"Generate and verify a working Dockerfile for the repository located at `{repo_path}`"

    try:

        inputs = {"messages": [HumanMessage(content=input_text)]}
        
        final_output = ""

        async for chunk, metadata in agent.astream(inputs, stream_mode="messages"):
            if isinstance(chunk, (AIMessage, AIMessageChunk)):
                if chunk.content:
                    final_output += chunk.content
                    
                if chunk.tool_calls:
                    for tool_call in chunk.tool_calls:
                        tool_name = tool_call["name"]
                        if tool_name == "analyze_repo":
                            console.print("[cyan]🤖 Agent is scanning the repository layout...[/cyan]")
                        elif tool_name == "read_file_content":
                            file_name = tool_call["args"].get("rel_path", "config")
                            console.print(f"[cyan]🤖 Agent is reading the content of [bold]{file_name}[/bold]...[/cyan]")
                        elif tool_name == "write_dockerfile_to_disk":
                            console.print("[cyan]🤖 Agent is writing the generated Dockerfile...[/cyan]")
                        elif tool_name == "build_docker_image_tool":
                            console.print("[cyan]🤖 Agent is triggering a local Docker build...[/cyan]")
                        elif tool_name == "verify_container_tool":
                            console.print("[cyan]🤖 Agent is launching the container to verify it starts...[/cyan]")
                            
        return final_output
    except Exception as e:
        logger.error(f"Agent execution encountered an error: {e}")
        raise e