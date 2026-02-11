# devops-info-service - FastAPI API

![Python CI](https://github.com/MoriSummerz/DevOps-Core-Course/actions/workflows/python-ci.yml/badge.svg)

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
    - [Python dependencies](#python-dependencies)
- [Installation](#installation)
- [Running the Application](#running-the-application)
- [API Endpoints](#api-endpoints)
- [Configuration](#configuration)
- [Docker](#docker)

## Overview

This is a simple web API built using FastAPI that provides DevOps-related information. The API has endpoints to retrieve
information about various DevOps tools and practices.

## Prerequisites

- Python 3.12+
- pip (Python package installer)
- Virtual environment (optional but recommended)

### Python dependencies

The application requires the following Python packages:

- `fastapi`
- `uvicorn`
- `pydantic`
- `pydantic_settings`

## Installation

1. Create virtual environment (optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```
2. Install dependencies:
   ```bash
    pip install -r requirements.txt
    ```

## Running the Application

To run the application locally, use the following command:

```bash
python3 app.py
```

The API will be accessible at `http://${HOST}:${PORT}`.
> You can set the `HOST` and `PORT` environment variables to customize the host and port. (see more in
> the [Configuration](#configuration) section)

## API Endpoints

- `GET /`: Service and system information.
- `GET /health`: Returns the health status of the API.

## Configuration

The application can be configured using environment variables:

- `HOST`: The host address to bind the server (default: `0.0.0.0`).
- `PORT`: The port number to bind the server (default: `5000`).
- `DEBUG`: Enable or disable debug mode (default: `False`).

> You can set these environment variables in your terminal or use `.env` file for local development (see `.env.example`
> file for reference).

## Testing

The application uses **pytest** as the testing framework.

### Why pytest?

- Simple and readable test syntax
- Powerful fixture system for test setup/teardown
- Excellent plugin ecosystem (pytest-cov, pytest-asyncio)
- Detailed test output and failure reports

### Running Tests

1. Install development dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```

2. Run all tests:
   ```bash
   pytest
   ```

3. Run tests with verbose output:
   ```bash
   pytest -v
   ```

4. Run tests with coverage report:
   ```bash
   pytest --cov=. --cov-report=term-missing
   ```

### Test Structure

```
tests/
├── conftest.py      # Shared fixtures (test client)
├── test_root.py     # Tests for GET / endpoint
└── test_health.py   # Tests for GET /health endpoint
```

## Linting

The project uses **Ruff** for linting and formatting:

```bash
# Check for linting errors
ruff check .

# Check formatting
ruff format --check .

# Auto-fix issues
ruff check --fix .
ruff format .
```

## Docker

The application can be containerized using Docker for consistent deployment across environments.

### Building the Image

Build the Docker image from the `app_python` directory:

```bash
docker build -t <image-name>:<tag> .
```

### Running a Container

Run a container from the built image with port mapping:

```bash
docker run -p <host-port>:<container-port> <image-name>:<tag>
```

To run in detached mode with environment variables:

```bash
docker run -d -p <host-port>:5000 -e DEBUG=true <image-name>:<tag>
```

### Pulling from Docker Hub

Pull the pre-built image from Docker Hub:

```bash
docker pull <dockerhub-username>/<repository>:<tag>
```

Then run it:

```bash
docker run -p 5000:5000 <dockerhub-username>/<repository>:<tag>
```

### Docker Commands Reference

| Command | Description |
|---------|-------------|
| `docker build` | Build an image from a Dockerfile |
| `docker run` | Create and start a container |
| `docker ps` | List running containers |
| `docker logs` | View container logs |
| `docker stop` | Stop a running container |