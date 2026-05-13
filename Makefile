.PHONY: clean lint test coverage coverage-badge wheel pyinstaller publish all

VERSION := $(shell python -c "from deep_coder import __version__; print(__version__)")

clean:
	rm -rf build/ dist/ *.egg-info coverage.xml htmlcov/

lint:
	ruff check deep_coder/ tests/

test:
	pytest tests/ -q

coverage:
	pytest --cov --cov-report=xml --cov-report=term-missing -q

coverage-badge: coverage
	python scripts/generate_badge.py

wheel: clean
	python -m build

pyinstaller: clean
	pyinstaller deep_coder.spec

publish: wheel
	twine upload dist/*

all: lint test wheel pyinstaller
