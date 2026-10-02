# Makefile for kestrel-router. Python 3.10+, no API key, no paid calls.
#
# PY selects the interpreter: the project's own .venv when it exists, otherwise the system
# python3. That matters on Windows, where bare `python` is usually a Microsoft Store alias that
# exits non-zero (errors.md E1) — so `make run` prefers .venv/Scripts/python.exe automatically.
# Override explicitly if needed:   make run PY=py
#
# Targets are plain shell commands; there is no parse-time side effect, so `make help` is safe.

PY ?= $(if $(wildcard .venv/Scripts/python.exe),.venv/Scripts/python.exe,$(if $(wildcard .venv/bin/python),.venv/bin/python,python3))

.PHONY: help setup run serve test pipeline check docker-build docker-run clean

help:
	@echo "setup         create .venv and install requirements-dev.txt"
	@echo "run / serve   start the API and the web page on $(PY)"
	@echo "test          run the pytest suite"
	@echo "pipeline      validate, audit, train, check -> artifacts/ and predictions.csv"
	@echo "check         validate the current predictions.csv"
	@echo "docker-build  build the image (ships the trained model)"
	@echo "docker-run    run the image, mounting ./data/input"
	@echo "clean         remove generated artifacts, keep the folder"

# Uses the system interpreter to create the venv, then PY for everything inside it.
setup:
	python3 -m venv .venv || py -m venv .venv
	"$(PY)" -m pip install --upgrade pip
	"$(PY)" -m pip install -r requirements-dev.txt

run serve:
	"$(PY)" -m kestrel serve

test:
	"$(PY)" -m pytest -q

pipeline:
	"$(PY)" -m kestrel run full_pipeline

check:
	"$(PY)" -m kestrel check

docker-build:
	docker build -t kestrel-router .

docker-run: docker-build
	docker run --rm -p 8000:8000 -v "$(CURDIR)/data/input:/app/data/input" kestrel-router

clean:
	rm -rf artifacts/* .pytest_cache
	touch artifacts/.gitkeep