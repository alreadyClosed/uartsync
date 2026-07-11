.PHONY: install install-system uninstall uninstall-system venv clean help

VENV := .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

venv:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

install: venv
	$(PIP) install .
	@echo '\nIf installed failed, try using "make install-system"'

install-system:
	python3 -m pip install -r requirements.txt --break-system-packages
	python3 -m pip install . --break-system-packages

uninstall:
	pip uninstall -y uartsync || true
	@echo '\nIf uninstalled failed, try using "make uninstall-system"'

uninstall-system:
	python3 -m pip uninstall -y uartsync --break-system-packages || true

clean:
	rm -rf $(VENV) build dist *.egg-info uartsync/__pycache__

help:
	@echo '\nOptions: install install-system uninstall uninstall-system venv clean help'

