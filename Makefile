SHELL := /bin/bash

.PHONY: setup install install-dev lint test run clean-setup clean-lint all clean

setup: install-dev
	uv run pre-commit install
	uv run pre-commit install --hook-type commit-msg

install:
	uv sync --no-default-groups

dev:
	uv sync --all-groups

lint:
	uv run pre-commit run --all-files

test:
	uv run pytest tests/* --cov-branch --cov=codecov --cov-report=term-missing

report:
	uv run pytest tests --cov-branch --cov=codecov --cov-report=term-missing --cov-report=json:/tmp/report.json

build:
	uv run python -m build

test-publish:
	uv run python -m twine upload --repository testpypi dist/*

publish:
	uv run python -m twine upload dist/*

run:
	uv run python run.py

clean-setup:
	uv run pre-commit uninstall --hook-type commit-msg
	uv run pre-commit uninstall

clean-lint:
	uv run pre-commit clean
	uv run pre-commit gc

all: setup lint

clean: clean-lint clean-setup
