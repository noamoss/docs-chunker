.PHONY: install lint fmt type test run clean

install:
	pip install -e ".[dev]"
	pip install "markitdown[docx]"

lint:
	ruff check src tests
	black --check src tests

fmt:
	black src tests

type:
	mypy src

test:
	pytest -v

run:
	python -m docs_chunker.cli

clean:
	find . -type d -name __pycache__ -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -r {} +
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage coverage.xml htmlcov
