.PHONY: help build run stop restart logs shell test health clean rebuild

# Default target
help:
    @echo "DeepStream Camera API - Docker Commands"
    @echo "========================================"
    @echo "make build    - Build Docker image"
    @echo "make run      - Start container"
    @echo "make stop     - Stop container"
    @echo "make restart  - Restart container"
    @echo "make logs     - View container logs"
    @echo "make shell    - Enter container shell"
    @echo "make test     - Test imports inside container"
    @echo "make health   - Check API health"
    @echo "make clean    - Remove container and volumes"
    @echo "make rebuild  - Clean, build, and run"
    @echo "make docs     - Open API documentation"

# Build Docker image
build:
    @echo "Building Docker image..."
    docker-compose build

# Start container
run:
    @echo "Starting container..."
    docker-compose up -d
    @echo "Container started! Access API at http://localhost:8000"
    @echo "View logs: make logs"

# Stop container
stop:
    @echo "Stopping container..."
    docker-compose down

# Restart container
restart: stop run

# View logs
logs:
    docker-compose logs -f camera-api

# Enter container shell
shell:
    docker exec -it deepstream-camera-api bash

# Test imports inside container
test:
    @echo "Testing imports..."
    docker exec -it deepstream-camera-api python3 check_imports.py

# Check API health
health:
    @echo "Checking API health..."
    @curl -s http://localhost:8000/camera/health | python3 -m json.tool || echo "API not responding"

# Open API documentation in browser
docs:
    @echo "Opening API documentation..."
    @xdg-open http://localhost:8000/docs 2>/dev/null || open http://localhost:8000/docs 2>/dev/null || echo "Please open http://localhost:8000/docs in your browser"

# Clean up everything
clean:
    @echo "Cleaning up..."
    docker-compose down -v
    docker system prune -f

# Full rebuild
rebuild: clean build run
    @echo "Rebuild complete!"

# Check if NVIDIA runtime is available
check-gpu:
    @echo "Checking NVIDIA GPU availability..."
    docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi