![Python CI](https://github.com/TovarishDru/DevOps-Core-Course/actions/workflows/python-ci.yml/badge.svg)


# DevOps Info Service

## Overview
A simple web service that exposes runtime, system, and request information.
This project serves as the foundation for future DevOps labs involving
containerization, CI/CD, monitoring, and Kubernetes.

## Prerequisites
- docker

## Installation
```bash
docker pull tovarishdru/devops-python-app:v1.0
```

**OR**

```bash
git clone https://github.com/TovarishDru/DevOps-Core-Course.git
cd ./DevOps-Core-Course
docker build -t devops-python-app ./app_python
```

## Running the Application
```bash
docker run -d -p 8000:8000 --name python-container devops-python-app
```

## Rinning tests locally

### The **venv** package and **Python** are required

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r ./app_python/requirements.txt
pip install -r ./app_python/dev-requirements.txt
pytest app_python
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
