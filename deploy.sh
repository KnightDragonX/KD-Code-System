#!/bin/bash
# Deployment Script for KD-Code System

set -e  # Exit on any error

echo "Starting KD-Code System deployment..."

# Check if we're in the right directory
if [ ! -f "app.py" ]; then
    echo "Error: app.py not found. Please run this script from the project root."
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed or not in PATH"
    exit 1
fi

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Warning: docker-compose is not installed. Attempting to use 'docker compose' (v2 syntax)..."
    if ! command -v docker &> /dev/null || ! docker compose version &> /dev/null; then
        echo "Error: Neither docker-compose nor docker compose is available"
        exit 1
    fi
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi

# Load environment variables
if [ -f ".env" ]; then
    echo "Loading environment variables from .env file..."
    export $(cat .env | xargs)
else
    echo "Warning: .env file not found. Using default values."
    export JWT_SECRET_KEY=$(openssl rand -hex 32)
fi

# Build and deploy
echo "Building and deploying KD-Code System..."
$COMPOSE_CMD down --remove-orphans 2>/dev/null || true
$COMPOSE_CMD build
$COMPOSE_CMD up -d

# Wait for services to be ready
echo "Waiting for services to be ready..."
sleep 10

# Run health check
echo "Running health check..."
HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/health || echo "error")

if [ "$HEALTH_STATUS" -eq 200 ]; then
    echo "✓ KD-Code System deployed successfully!"
    echo "✓ Health check passed (HTTP $HEALTH_STATUS)"
    echo "✓ Application is running at http://localhost:5000"
    echo ""
    echo "Deployment Summary:"
    echo "- Web Service: http://localhost:5000"
    echo "- Health Check: http://localhost:5000/health"
    echo "- Metrics: http://localhost:5000/metrics"
    echo "- Ready Check: http://localhost:5000/health/ready"
else
    echo "✗ Health check failed (HTTP $HEALTH_STATUS)"
    echo "✗ Deployment may have failed. Check logs with: $COMPOSE_CMD logs"
    exit 1
fi

echo ""
echo "Deployment completed successfully!"