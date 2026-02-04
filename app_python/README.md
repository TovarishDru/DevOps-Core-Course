# DevOps Info Service

## Overview
A simple web service that exposes runtime, system, and request information.
This project serves as the foundation for future DevOps labs involving
containerization, CI/CD, monitoring, and Kubernetes.

## Prerequisites
- Python 3.11+
- pip

## Installation
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Running the Application
```bash
python app.py
# Or with custom config
PORT=8080 HOST=127.0.0.1 DEBUG=true python app.py
```

## API Endpoints

### GET /

Returns service, system, runtime, and request information.

### GET /health

Health check endpoint for monitoring systems.


## Configuration

| Variable | Default | Description       |
| -------- | ------- | ----------------- |
| HOST     | 0.0.0.0 | Bind address      |
| PORT     | 5000    | Server port       |
| DEBUG    | false   | Enable debug mode |
