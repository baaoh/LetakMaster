# Use a standard Linux Python image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies (for PostgreSQL support)
RUN apt-get update && apt-get install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*

# Copy only the necessary parts of the project
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY core/ ./core/
COPY server/ ./server/

# Expose the port the Hub runs on
EXPOSE 8000

# Start the FastAPI Hub
CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
