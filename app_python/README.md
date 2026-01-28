# devops-info-service - FastAPI API

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
    - [Python dependencies](#python-dependencies)
- [Installation](#installation)
- [Running the Application](#running-the-application)
- [API Endpoints](#api-endpoints)
- [Configuration](#configuration)

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