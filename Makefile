 .PHONY: install lint fmt type test run

install:
	@echo "Installing deps with pip in existing venv"
	. .venv/bin/activate && pip install -U pip setuptools wheel && \
		pip install typer pydantic pyyaml rich fastapi uvicorn httpx pytest pytest-mock pytest-cov ruff black mypy markitdown

lint:
	black --check src tests

fmt:
	black src tests

type:
	mypy src

test:
	pytest

run:
	python -m docs_chunker.cli --help
