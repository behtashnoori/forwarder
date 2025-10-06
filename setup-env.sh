#!/bin/bash

# اسکریپت ایجاد فایل‌های محیطی
echo "🔧 Setting up environment files..."

# Create backend .env.production if it doesn't exist
if [ ! -f "backend/.env.production" ]; then
    echo "📝 Creating backend/.env.production..."
    cp backend/env.production.example backend/.env.production
    echo "✅ Created backend/.env.production"
    echo "⚠️  Please edit this file with your actual values!"
else
    echo "✅ backend/.env.production already exists"
fi

# Create backend .env.docker if it doesn't exist
if [ ! -f "backend/.env.docker" ]; then
    echo "📝 Creating backend/.env.docker..."
    cp backend/env.docker.example backend/.env.docker
    echo "✅ Created backend/.env.docker"
else
    echo "✅ backend/.env.docker already exists"
fi

# Create instance directory for logs
if [ ! -d "instance/logs" ]; then
    echo "📁 Creating instance/logs directory..."
    mkdir -p instance/logs
    echo "✅ Created instance/logs directory"
else
    echo "✅ instance/logs directory already exists"
fi

# Create backup directory
if [ ! -d "backup" ]; then
    echo "📁 Creating backup directory..."
    mkdir -p backup
    echo "✅ Created backup directory"
else
    echo "✅ backup directory already exists"
fi

echo ""
echo "🎉 Environment setup completed!"
echo ""
echo "📋 Next steps:"
echo "1. Edit backend/.env.production with your actual values"
echo "2. Set DB_PASSWORD environment variable: export DB_PASSWORD='your-secure-password'"
echo "3. Run deployment: ./deploy.sh"