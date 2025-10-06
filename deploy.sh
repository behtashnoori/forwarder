#!/bin/bash

# اسکریپت deployment برای production
echo "🚀 Starting deployment..."

# Check if environment files exist
if [ ! -f "backend/.env.production" ]; then
    echo "⚠️  Creating .env.production from example..."
    cp backend/env.production.example backend/.env.production
    echo "📝 Please edit backend/.env.production with your actual values!"
    echo "   - SECRET_KEY: Change to a strong secret key"
    echo "   - CORS_ORIGIN: Set to your domain"
    echo "   - DB_PASSWORD: Set via environment variable"
fi

# Check if DB_PASSWORD is set
if [ -z "$DB_PASSWORD" ]; then
    echo "⚠️  DB_PASSWORD environment variable not set!"
    echo "   Please set it with: export DB_PASSWORD='your-secure-password'"
    exit 1
fi

# Stop existing containers
echo "🛑 Stopping existing containers..."
docker-compose -f docker-compose.production.yml down

# Build and start new containers
echo "🔨 Building and starting containers..."
docker-compose -f docker-compose.production.yml up --build -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 45

# Check API health
echo "🏥 Checking API health..."
max_attempts=10
attempt=1
while [ $attempt -le $max_attempts ]; do
    if docker-compose -f docker-compose.production.yml exec -T api curl -f http://localhost:5000/api/health > /dev/null 2>&1; then
        echo "✅ API is healthy!"
        break
    else
        echo "⏳ Waiting for API... (attempt $attempt/$max_attempts)"
        sleep 10
        attempt=$((attempt + 1))
    fi
done

# Run database migrations
echo "📊 Running database migrations..."
docker-compose -f docker-compose.production.yml exec -T api python -m flask db upgrade

# Show running containers
echo "✅ Deployment completed!"
echo "📊 Service Status:"
docker-compose -f docker-compose.production.yml ps

echo ""
echo "🌐 Services are now available:"
echo "   - Frontend: http://$(hostname -I | awk '{print $1}')/"
echo "   - API Health: http://$(hostname -I | awk '{print $1}')/api/health"
echo "   - Database Admin: http://$(hostname -I | awk '{print $1}'):8080"
echo ""
echo "📋 To view logs:"
echo "   docker-compose -f docker-compose.production.yml logs -f"
