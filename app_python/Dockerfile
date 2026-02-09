FROM python:3.13-slim

# Environment variables
ENV HOST=0.0.0.0
ENV PORT=8000
ENV DEBUG=false

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# Copy requirements file first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Change ownership to non-root user
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port (documentation only - doesn't publish port)
EXPOSE 8000

# Command to run the application
CMD ["python3", "app.py"]