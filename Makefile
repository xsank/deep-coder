.PHONY: clean lint test wheel pyinstaller publish all

VERSION := $(shell python -c "from deep_coder import __version__; print(__version__)")

clean:
	rm -rf build/ dist/ *.egg-info

lint:
	ruff check deep_coder/ tests/

test:
	pytest tests/ -q

wheel: clean
	python -m build

pyinstaller: clean
	pyinstaller deep_coder.spec

publish: wheel
	twine upload dist/*

all: lint test wheel pyinstaller
