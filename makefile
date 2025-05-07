PYTHON = python3
PIP = pip3
VENV_DIR = venv
REQUIREMENTS = requirements.txt
SCRIPT = main.py
POSTGRES_IMAGE = postgres:15
POSTGRES_CONTAINER = postgres-container
POSTGRES_PORT = 5432
POSTGRES_USER = test_user
POSTGRES_PASSWORD = test_password
POSTGRES_DB = test_db

setup:
	@echo "Setting up virtual environment..."
	$(PYTHON) -m venv $(VENV_DIR)
	$(VENV_DIR)/bin/$(PIP) install --upgrade pip
	$(VENV_DIR)/bin/$(PIP) install -r $(REQUIREMENTS)

run:	setup
	@echo "Running transcription script..."
	$(VENV_DIR)/bin/$(PYTHON) $(SCRIPT)

clean:
	@echo "Cleaning up temporary files and virtual environment..."
	rm -rf $(TEMP_DIR)
	rm -rf $(VENV_DIR)

install-ffmpeg:
	@echo "Installing ffmpeg..."
	sudo apt update && sudo apt install -y ffmpeg

start-postgres:
	@echo "Starting PostgreSQL container..."
	docker run --name $(POSTGRES_CONTAINER) \
		-e POSTGRES_USER=$(POSTGRES_USER) \
		-e POSTGRES_PASSWORD=$(POSTGRES_PASSWORD) \
		-e POSTGRES_DB=$(POSTGRES_DB) \
		-p $(POSTGRES_PORT):5432 \
		-d $(POSTGRES_IMAGE)

stop-postgres:
	@echo "Stopping and removing PostgreSQL container..."
	docker stop $(POSTGRES_CONTAINER) || true
	docker rm $(POSTGRES_CONTAINER) || true

help:
	@echo "Available commands:"
	@echo "  make setup          - Set up the virtual environment and install dependencies"
	@echo "  make run            - Run the transcription script"
	@echo "  make clean          - Clean up temporary files and virtual environment"
	@echo "  make install-ffmpeg - Install ffmpeg (Linux-specific)"
	@echo "  make start-postgres - Start a local PostgreSQL container for testing"
	@echo "  make stop-postgres  - Stop and remove the local PostgreSQL container"