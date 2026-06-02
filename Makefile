.PHONY: install run clean lint

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
