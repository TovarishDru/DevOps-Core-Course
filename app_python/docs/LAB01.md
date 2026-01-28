# LAB01 — DevOps Info Service

## Framework Selection

### Chosen Framework: Flask

Flask was selected as the web framework for this lab because it is lightweight, simple to configure, and well-suited for building small REST-style services. Since the goal of this lab is to expose system and runtime information rather than build a full-featured web application, Flask provides exactly the right level of abstraction without unnecessary complexity

### Framework Comparison

| Framework | Advantages | Disadvantages |
| --- | --- | --- |
| Flask | — Lightweight; <br> — easy to learn; <br> — minimal boilerplate; <br> — great for microservices. | — No built-in async support |
| FastAPI | — Async support; <br> — automatic OpenAPI docs; <br> — strong typing. | — More complex setup; <br> — steeper learning curve |
| Django | — Full-featured framework; <br> — ORM included; <br> — scalable. | — Overkill for simple services; <br> — heavier configuration |

Flask was chosen because it best matches the simplicity and educational goals of this lab

## Best Practices Applied

1. **Clean Code Organization**

    Functions are clearly separated by responsibility (system info, uptime calculation, routes). Imports are grouped logically, and meaningful function names are used

    **Why it matters:**
    Clean code improves readability, maintainability, and makes future extensions (Docker, monitoring, CI/CD) easier

2. **Environment-Based Configuration**

    The application is configurable using environment variables for host, port, and debug mode

    **Why it matters:**
    Environment-based configuration is essential for containerized and cloud deployments, where applications must adapt to different environments without code changes

3. **Logging**

    Structured logging is enabled for application startup, requests, and error handling

    **Why it matters:**
    Logging is critical for debugging, monitoring, and observability in production systems and is a core DevOps practice

4. **Error Handling**

    Custom handlers for HTTP 404 and 500 errors return consistent JSON responses

    **Why it matters:**
    Graceful error handling improves reliability and provides clear feedback to users and monitoring systems

5. **Dependency Management**

    All dependencies are pinned in `requirements.txt`

    **Why it matters:**
    Pinned versions ensure reproducible builds and consistent behavior across environments

## API Documentation

### Main Endpoint — GET /

Returns service metadata, system information, runtime details, request data, and available endpoints

**Request:**

```bash
curl http://localhost:5000/
```

**Response:**

```json
{
  "service": {
    "name": "devops-info-service",
    "version": "1.0.0",
    "description": "DevOps course info service",
    "framework": "Flask"
  },
  "system": {
    "hostname": "my-laptop",
    "platform": "Linux",
    "platform_version": "Ubuntu 24.04",
    "architecture": "x86_64",
    "cpu_count": 8,
    "python_version": "3.13.1"
  },
  "runtime": {
    "uptime_seconds": 3600,
    "uptime_human": "1 hour, 0 minutes",
    "current_time": "2026-01-07T14:30:00.000Z",
    "timezone": "UTC"
  },
  "request": {
    "client_ip": "127.0.0.1",
    "user_agent": "curl/7.81.0",
    "method": "GET",
    "path": "/"
  },
  "endpoints": [
    {"path": "/", "method": "GET", "description": "Service information"},
    {"path": "/health", "method": "GET", "description": "Health check"}
  ]
}
```

### Health Check — GET /health

**Request:**

```bash
curl http://localhost:5000/health
```

**Response:**

```json
{
  "status": "healthy",
  "timestamp": "2026-01-07T14:30:00Z",
  "uptime_seconds": 3600
}
```

### Pretty-Printed Output

```bash
curl http://localhost:5000/ | jq
```

## Testing Evidence

![Testing results](./TestEvidence.png)

## Chalenges & Solutions

### Challenge 1: Uptime Calculation

**Problem:**

Representing uptime in both seconds and a human-readable format

**Solution:**

Used the datetime module to track application start time and compute uptime dynamically

### Challenge 2: Logging Errors Correctly

**Problem:**

Ensuring that client errors (404) and server errors (500) were logged appropriately

**Solution:**
Implemented separate logging levels:

- logger.warning for 404 errors

- logger.exception for 500 errors to include stack traces

### Challenge 3: Consistent JSON Responses

**Problem:**
Default Flask error pages return HTML responses

**Solution:**
Added custom error handlers to return structured JSON responses for all errors

## GitHub Community

Starring repositories helps recognize valuable open-source projects, increases their visibility, and signals community trust, which encourages maintainers and contributors to continue improving the software

Following developers supports collaboration and professional growth by making it easier to learn from others’ work, stay aware of ongoing projects, and build connections for effective team-based development
