.PHONY: install run clean lint docker-build docker-run

install:
	uv sync

run:
	uv run main.py

clean:
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type d -name ".pytest_cache" -exec rm -r {} +
	rm -rf .tmp_repos
	rm -f *.tar

lint:
	uvx ruff check .
	uvx ruff format --check .

# Build the Docker image in one step
docker-build:
	docker build -t dockerforge .

# Run the Docker image in one step (for standard Linux/macOS)
docker-run:
# 	docker run -it -v /var/run/docker.sock:/var/run/docker.sock --env-file .env dockerforge
	docker run -it -v /var/run/docker.sock:/var/run/docker.sock -v $(shell pwd)/.tmp_repos:/app/.tmp_repos --env-file .env dockerforge
