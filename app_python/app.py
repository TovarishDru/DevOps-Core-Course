import os
import socket
import platform
import logging
import json
import time
from datetime import datetime, timezone
from flask import Flask, jsonify, request, Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CollectorRegistry, CONTENT_TYPE_LATEST


# JSON Formatter for structured logging
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add extra fields if present
        if hasattr(record, "method"):
            log_data["method"] = record.method
        if hasattr(record, "path"):
            log_data["path"] = record.path
        if hasattr(record, "status_code"):
            log_data["status_code"] = record.status_code
        if hasattr(record, "client_ip"):
            log_data["client_ip"] = record.client_ip
        if hasattr(record, "user_agent"):
            log_data["user_agent"] = record.user_agent
            
        return json.dumps(log_data)


# Configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 5000))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

SERVICE_NAME = "devops-info-service"
SERVICE_VERSION = "1.0.0"
SERVICE_DESCRIPTION = "DevOps course info service"
FRAMEWORK = "Flask"


# App setup
app = Flask(__name__)
START_TIME = datetime.now(timezone.utc)

# Configure JSON logging
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(handler)

# Also configure root logger for Flask
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.handlers = []
root_logger.addHandler(handler)

logger.info("Application starting", extra={
    "service": SERVICE_NAME,
    "version": SERVICE_VERSION,
    "port": PORT
})


# Prometheus Metrics
# Counter: Total HTTP requests
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

# Histogram: Request duration
http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0)
)

# Gauge: Active requests
http_requests_in_progress = Gauge(
    'http_requests_in_progress',
    'HTTP requests currently being processed',
    ['method', 'endpoint']
)

# Application-specific metrics
endpoint_calls = Counter(
    'devops_info_endpoint_calls',
    'Number of calls to specific endpoints',
    ['endpoint']
)

system_info_collection_duration = Histogram(
    'devops_info_system_collection_seconds',
    'Time spent collecting system information',
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0)
)


# Helper functions
def get_uptime():
    delta = datetime.now(timezone.utc) - START_TIME
    seconds = int(delta.total_seconds())
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60

    return {
        "seconds": seconds,
        "human": f"{hours} hours, {minutes} minutes",
    }


def get_system_info():
    start_time = time.time()
    info = {
        "hostname": socket.gethostname(),
        "platform": platform.system(),
        "platform_version": platform.version(),
        "architecture": platform.machine(),
        "cpu_count": os.cpu_count(),
        "python_version": platform.python_version(),
    }
    duration = time.time() - start_time
    system_info_collection_duration.observe(duration)
    return info


def normalize_endpoint(path):
    """Normalize endpoint paths to reduce cardinality"""
    if path == '/':
        return '/'
    elif path == '/health':
        return '/health'
    elif path == '/metrics':
        return '/metrics'
    else:
        return '/other'


# Request/Response logging and metrics middleware
@app.before_request
def before_request():
    request.start_time = time.time()
    endpoint = normalize_endpoint(request.path)
    
    # Increment in-progress gauge
    http_requests_in_progress.labels(
        method=request.method,
        endpoint=endpoint
    ).inc()
    
    logger.info("Incoming request", extra={
        "method": request.method,
        "path": request.path,
        "client_ip": request.remote_addr,
        "user_agent": request.headers.get("User-Agent", "Unknown")
    })


@app.after_request
def after_request(response):
    endpoint = normalize_endpoint(request.path)
    
    # Calculate request duration
    if hasattr(request, 'start_time'):
        duration = time.time() - request.start_time
        
        # Record metrics
        http_request_duration_seconds.labels(
            method=request.method,
            endpoint=endpoint
        ).observe(duration)
    
    # Increment request counter
    http_requests_total.labels(
        method=request.method,
        endpoint=endpoint,
        status=response.status_code
    ).inc()
    
    # Decrement in-progress gauge
    http_requests_in_progress.labels(
        method=request.method,
        endpoint=endpoint
    ).dec()
    
    logger.info("Outgoing response", extra={
        "method": request.method,
        "path": request.path,
        "status_code": response.status_code,
        "client_ip": request.remote_addr
    })
    
    return response


# Routes
@app.route("/", methods=["GET"])
def index():
    endpoint_calls.labels(endpoint='/').inc()
    uptime = get_uptime()

    response = {
        "service": {
            "name": SERVICE_NAME,
            "version": SERVICE_VERSION,
            "description": SERVICE_DESCRIPTION,
            "framework": FRAMEWORK,
        },
        "system": get_system_info(),
        "runtime": {
            "uptime_seconds": uptime["seconds"],
            "uptime_human": uptime["human"],
            "current_time": datetime.now(timezone.utc).isoformat(),
            "timezone": "UTC",
        },
        "request": {
            "client_ip": request.remote_addr,
            "user_agent": request.headers.get("User-Agent"),
            "method": request.method,
            "path": request.path,
        },
        "endpoints": [
            {"path": "/", "method": "GET", "description": "Service information"},
            {"path": "/health", "method": "GET", "description": "Health check"},
            {"path": "/metrics", "method": "GET", "description": "Prometheus metrics"},
        ],
    }

    return jsonify(response)


@app.route("/health", methods=["GET"])
def health():
    endpoint_calls.labels(endpoint='/health').inc()
    uptime = get_uptime()

    return jsonify(
        {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "uptime_seconds": uptime["seconds"],
        }
    )


@app.route("/metrics", methods=["GET"])
def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


@app.route("/error", methods=["GET"])
def trigger_error():
    """Endpoint that intentionally returns 500 error for testing"""
    endpoint_calls.labels(endpoint='/error').inc()
    
    logger.error("Intentional error triggered", extra={
        "method": request.method,
        "path": request.path,
        "client_ip": request.remote_addr,
        "status_code": 500
    })
    
    return jsonify(
        {
            "error": "Internal Server Error",
            "message": "This is an intentional error for testing metrics",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    ), 500


@app.route("/bad-request", methods=["GET"])
def bad_request():
    """Endpoint that returns 400 Bad Request for testing"""
    endpoint_calls.labels(endpoint='/bad-request').inc()
    
    logger.warning("Bad request triggered", extra={
        "method": request.method,
        "path": request.path,
        "client_ip": request.remote_addr,
        "status_code": 400
    })
    
    return jsonify(
        {
            "error": "Bad Request",
            "message": "This is an intentional 400 error for testing client error metrics",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    ), 400


# Error Handlers
@app.errorhandler(404)
def not_found(error):
    logger.warning("404 Not Found", extra={
        "method": request.method,
        "path": request.path,
        "client_ip": request.remote_addr,
        "status_code": 404
    })

    return jsonify(
        {
            "error": "Not Found",
            "message": "Endpoint does not exist",
        }
    ), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error("500 Internal Server Error", extra={
        "method": request.method,
        "path": request.path,
        "client_ip": request.remote_addr,
        "status_code": 500,
        "error": str(error)
    })

    return jsonify(
        {
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
        }
    ), 500


# Entry point
if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=DEBUG)
