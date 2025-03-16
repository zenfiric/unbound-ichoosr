# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set build-time arguments
ARG PORT=8989
ARG OPENAI_API_KEY=
ARG SYSTEM_MESSAGE=

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=${PORT} \
    OPENAI_API_KEY=${OPENAI_API_KEY} \
    SYSTEM_MESSAGE=${SYSTEM_MESSAGE}

# Set working directory
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install system dependencies including netcat
RUN apt-get update && \
    apt-get install -y \
        graphviz \
        xdg-utils && \
    rm -rf /var/lib/apt/lists/*

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Expose port
EXPOSE ${PORT}

# ${PORT} is not expanded inside a JSON array (CMD ["..."]).
CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT} --reload"]
