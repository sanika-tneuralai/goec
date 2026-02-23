

This is a comprehensive camera management and analytics system using DeepStream and YOLO.

## Project Structure

```
GOEC/
├── backend/          # Backend API and services (formerly sakshi)
│   ├── alert/        # Alert management
│   ├── analytics/    # Analytics and metrics
│   ├── camera/       # Camera management
│   ├── common/       # Common utilities
│   ├── config/       # Configuration management
│   ├── database/     # Database models and connections
│   ├── detection/    # Object detection
│   ├── usecase/      # Use case implementations
│   ├── models/       # YOLO model files
│   ├── main.py       # FastAPI application entry point
│   ├── Dockerfile    # Docker configuration
│   └── docker-compose.yml  # Docker Compose configuration
│
├── frontend/         # Frontend application (to be implemented)
│
└── yolo_clean/       # Python virtual environment
```

## Backend

The backend is built with FastAPI and integrates with NVIDIA DeepStream for real-time video processing.

### Quick Start

```bash
cd backend

# Build and run with Docker
make build
make run

# Or run locally
python3 main.py
```

### Available Make Commands

- `make build` - Build Docker image
- `make run` - Start container
- `make stop` - Stop container
- `make logs` - View logs
- `make shell` - Enter container shell
- `make health` - Check API health
- `make docs` - Open API documentation

### API Documentation

Once running, access the API documentation at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Frontend

Frontend development folder. Add your preferred frontend framework here.

## Database Setup

Run the database setup script:
```bash
cd backend
./setup_db.sh
```

## Testing

```bash
cd backend
./test_api.sh
```

## Requirements

- NVIDIA GPU with CUDA support
- NVIDIA DeepStream 6.4
- Docker with NVIDIA runtime
- PostgreSQL

## License

[Add license information]
