#!/bin/bash

# اسکریپت deployment برای production
echo "🚀 Starting deployment..."

# Stop existing containers
echo "🛑 Stopping existing containers..."
docker-compose -f docker-compose.production.yml down

# Build and start new containers
echo "🔨 Building and starting containers..."
docker-compose -f docker-compose.production.yml up --build -d

# Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
sleep 30

# Run database migrations
echo "📊 Running database migrations..."
docker-compose -f docker-compose.production.yml exec api python -m flask db upgrade

# Show running containers
echo "✅ Deployment completed!"
docker-compose -f docker-compose.production.yml ps
