.ONESHELL:

PYTHON = python3
PIP = pip3
VENV_DIR = venv
REQUIREMENTS = requirements.txt
SCRIPT = main.py

# PostgreSQL specific settings
POSTGRES_IMAGE = postgres:15
POSTGRES_CONTAINER = postgres-container
POSTGRES_PORT = 5432
POSTGRES_USER = test_user
POSTGRES_PASSWORD = test_password
POSTGRES_DB = test_db

# Application-specific environment variables
PRODUCTION = false 
LOG_LEVEL = DEBUG
LOG_FILE = pipeline.log
URL = https://soundcloud.com/hmaqbul/ramad-n-late-night-majlis-two
IS_PLAYLIST = false
DATABASE_URL = postgresql://$(POSTGRES_USER):$(POSTGRES_PASSWORD)@localhost:$(POSTGRES_PORT)/$(POSTGRES_DB)

# Define temporary directories
TMP_DIR = tmp
AUDIO_DIR = $(TMP_DIR)/audio
TRANSCRIPT_DIR = $(TMP_DIR)/transcripts

init-dirs:
	@echo "Initializing temporary directories..."
	mkdir -p $(AUDIO_DIR)
	mkdir -p $(TRANSCRIPT_DIR)

setup:	init-dirs
	@echo "Setting up virtual environment..."
	$(PYTHON) -m venv $(VENV_DIR)
	$(VENV_DIR)/bin/$(PIP) install -r $(REQUIREMENTS)

run:
	@echo "Running..."
	export PRODUCTION=$(PRODUCTION)
	export LOG_LEVEL=$(LOG_LEVEL)
	export LOG_FILE=$(LOG_FILE)
	export URL=$(URL)
	export IS_PLAYLIST=$(IS_PLAYLIST)
	export DATABASE_URL=$(DATABASE_URL)
	export TMP_DIR=$(TMP_DIR)
	export AUDIO_DIR=$(AUDIO_DIR)
	export TRANSCRIPT_DIR=$(TRANSCRIPT_DIR)
	$(VENV_DIR)/bin/$(PYTHON) $(SCRIPT)

clean-hard:
	@echo "Cleaning up temporary directories and virtual environment..."
	rm -rf $(TMP_DIR)
	rm -rf $(VENV_DIR)

install-prerequisites:
	@echo "Updating package lists..."
	sudo apt-get update
	@echo "Installing ffmpeg..."
	sudo apt update && sudo apt install -y ffmpeg
	@echo "Installing PostgreSQL client..."
	sudo apt-get install -y postgresql-client

start-postgres:
	@echo "Starting PostgreSQL container..."
	docker run --name $(POSTGRES_CONTAINER) \
		-e POSTGRES_USER=$(POSTGRES_USER) \
		-e POSTGRES_PASSWORD=$(POSTGRES_PASSWORD) \
		-e POSTGRES_DB=$(POSTGRES_DB) \
		-p $(POSTGRES_PORT):5432 \
		-d $(POSTGRES_IMAGE)

migration:
	@echo "Running database migrations..."
	$(VENV_DIR)/bin/alembic revision --autogenerate
	$(VENV_DIR)/bin/alembic upgrade head

stop-postgres:
	@echo "Stopping and removing PostgreSQL container..."
	docker stop $(POSTGRES_CONTAINER) || true
	docker rm $(POSTGRES_CONTAINER) || true

help:
	@echo "Available commands:"
	@echo "  make setup          			- Set up the virtual environment and install dependencies"
	@echo "  make run            			- Run the transcription script"
	@echo "  make clean-hard     			- Clean up temporary files and virtual environment"
	@echo "  make install-prerequisites 	- Install ffmpeg and PostgreSQL client (Linux-specific)"
	@echo "  make start-postgres 			- Start a local PostgreSQL container for testing" # Assuming POSTGRES_IMAGE etc. are defined
	@echo "  make stop-postgres  			- Stop and remove the local PostgreSQL container" # Assuming POSTGRES_CONTAINER is defined
	@echo "  make help                   	- Show this help message"