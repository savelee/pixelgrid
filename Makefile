# Copyright 2026 Google LLC

.PHONY: setup test run-once docker-build docker-run

setup:
	uv venv .venv
	uv pip install -e ".[dev]"

test:
	uv run pytest tests/ -v

run-once:
	uv run python src/script.py --once

docker-build:
	docker build -t pixelgrid:latest .

docker-run:
	docker run --rm --network host --privileged \
		-v /var/run/dbus:/var/run/dbus \
		-v $(PWD)/downloads:/app/downloads \
		-e GCP_PROJECT_ID=leeboonstra \
		pixelgrid:latest
