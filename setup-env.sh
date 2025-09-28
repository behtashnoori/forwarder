#!/bin/bash

# اسکریپت تنظیم متغیرهای محیطی
echo "🔧 Setting up environment files..."

# کپی کردن فایل‌های نمونه
if [ ! -f "backend/.env.production" ]; then
    cp backend/env.production.example backend/.env.production
    echo "✅ Created backend/.env.production from example"
else
    echo "⚠️  backend/.env.production already exists"
fi

if [ ! -f "backend/.env.docker" ]; then
    cp backend/env.docker.example backend/.env.docker
    echo "✅ Created backend/.env.docker from example"
else
    echo "⚠️  backend/.env.docker already exists"
fi

# ایجاد پوشه backup
mkdir -p backup
echo "✅ Created backup directory"

# تنظیم دسترسی‌ها
chmod +x deploy.sh
echo "✅ Set execute permission on deploy.sh"

echo ""
echo "🎯 Next steps:"
echo "1. Edit backend/.env.production and set your SECRET_KEY and CORS_ORIGIN"
echo "2. Set DB_PASSWORD environment variable: export DB_PASSWORD='your-password'"
echo "3. Run ./deploy.sh to start the application"
echo ""
echo "📖 For detailed instructions, see DEPLOYMENT.md"
