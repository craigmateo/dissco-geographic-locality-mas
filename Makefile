.PHONY: setup test demo

PYTHON = .venv/bin/python

setup:
	python3 -m venv .venv
	$(PYTHON) -m pip install -e ".[dev]"

test:
	$(PYTHON) -m pytest -q

demo:
	$(PYTHON) -m geographic_locality_mas.cli

fetch:
	$(PYTHON) scripts/fetch_specimens.py
