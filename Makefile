.PHONY: install install-system uninstall venv clean

VENV := .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

venv:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

install: venv
	$(PIP) install .

install-system:
	python3 -m pip install -r requirements.txt --break-system-packages
	python3 -m pip install . --break-system-packages

uninstall:
	pip uninstall -y uartsync || true

clean:
	rm -rf $(VENV) build dist *.egg-info uartsync/__pycache__
