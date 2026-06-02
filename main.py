import sys
import re
import asyncio
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt
from rich.syntax import Syntax

from utils.git_utils import clone_repo
from utils.logger import logger
from agent.workflow import run_agent

# Initialize Rich Console
console = Console()

def print_banner():
    """Prints a beautiful, premium console banner for DockerForge."""
    banner_text = Text()
    banner_text.append("█▀▀▄ █▀▀█ █▀▀ █░█ █▀▀ █▀▀█ █▀▀ █▀▀█ █▀▀█ █▀▀█ █▀▀\n", style="bold cyan")
    banner_text.append("█░░█ █░░█ █░░ █▀▄ █▀▀ █▄▄▀ █▀▀ █░░█ █▄▄▀ █░░█ █▀▀\n", style="bold blue")
    banner_text.append("▀▀▀░ ▀▀▀▀ ▀▀▀ ▀░▀ ▀▀▀ ▀░▀▀ ▀░░ ▀▀▀▀ ▀░▀▀ █▀▀▀ ▀▀▀\n", style="bold magenta")
    banner_text.append("   ★ AI-Powered Dockerfile Generator & Verifier ★   \n", style="bold italic yellow")
    
    panel = Panel(
        banner_text,
        border_style="cyan",
        title="[bold white]v1.0.0[/bold white]",
        title_align="right",
        subtitle="[dim white]Built for DevOps & Agentic AI[/dim white]",
        subtitle_align="center"
    )
    console.print(panel)

def extract_dockerfile(text: str) -> str:
    """Extracts the Dockerfile contents from markdown code blocks in the agent response."""
    # Look for ```dockerfile ... ``` block
    match = re.search(r"```dockerfile\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    # Fallback to general ``` ... ``` blocks
    match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
        
    return text.strip()

def main():
    print_banner()
    
    # 1. Get repository URL from user
    repo_url = Prompt.ask("[bold white]Enter public GitHub Repository URL[/bold white]")
    repo_url = repo_url.strip()
    
    if not repo_url:
        console.print("[red]Error: Repository URL cannot be empty.[/red]")
        sys.exit(1)
        
    local_path = None
    
    try:
        # 2. Clone repository deterministically with a loading spinner
        with console.status("[bold yellow]Cloning repository shallowly (depth=1)...[/bold yellow]"):
            local_path = clone_repo(repo_url)
            
        console.print(f"[green]✔ Repository cloned successfully to:[/] [cyan]{local_path}[/]\n")
        
        # 3. Invoke the LangGraph Agent to generate and verify the Dockerfile
        # This will stream its node outputs automatically via workflow.py
        agent_output = asyncio.run(run_agent(local_path))
        
        # 4. Display the Final Working Results
        console.print("\n" + "="*50)
        console.print("[bold green]✔ DOCKERFORGE AGENT COMPLETED SUCCESSFULLY[/bold green]")
        console.print("="*50 + "\n")
        
        # Extract and print Dockerfile in syntax highlighted panel
        dockerfile_content = extract_dockerfile(agent_output)
        
        syntax = Syntax(
            dockerfile_content, 
            "dockerfile", 
            theme="monokai", 
            line_numbers=True,
            word_wrap=True
        )
        
        console.print(Panel(
            syntax, 
            title="[bold green]FINAL WORKING DOCKERFILE[/bold green]", 
            border_style="green",
            expand=False
        ))
        
        # Display the explanation / summary
        console.print(Panel(
            agent_output, 
            title="[bold cyan]Agent Execution Summary[/bold cyan]",
            border_style="cyan"
        ))
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Execution interrupted by user. Exiting...[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[bold red]✖ Error: {str(e)}[/bold red]")
        sys.exit(1)

if __name__ == "__main__":
    main()
