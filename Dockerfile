FROM python:3.12-slim

# Install git (required by gitpython) and curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Layer caching: Copy dependency manifests first
COPY pyproject.toml uv.lock ./

# Install project dependencies (not the project itself yet)
RUN uv pip install --system --no-cache-dir -r pyproject.toml

# Copy the rest of the source code
COPY . .

# DockerForge requires access to the host Docker socket
# Mount at runtime: -v /var/run/docker.sock:/var/run/docker.sock

# Keep root user for Docker socket access (DockerForge needs it)

# Set the entrypoint
CMD ["python", "main.py"]