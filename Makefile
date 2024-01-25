SHELL := /bin/bash

.PHONY: setup setup-pipenv install install-dev lint test run clean-setup clean-lint all clean

setup: install-dev
	pipenv run pre-commit install
	pipenv run pre-commit install --hook-type commit-msg

setup-pipenv:
	python -m pip install --upgrade pip
	pip install pipenv

install:
	pipenv sync

install-dev:
	pipenv sync --dev

lint:
	pipenv run pre-commit run --all-files

test:
	pipenv run pytest tests/* --cov

run:
	pipenv run python run.py

clean-setup:
	pipenv run pre-commit uninstall --hook-type commit-msg
	pipenv run pre-commit uninstall
	pipenv clean

clean-lint:
	pipenv run pre-commit clean
	pipenv run pre-commit gc

all: setup-pipenv setup lint run

clean: clean-lint clean-setup
