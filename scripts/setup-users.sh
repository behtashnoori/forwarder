#!/bin/bash

# Setup Users Script
# Creates/updates admin and expert users

echo "============================================================"
echo "🔧 ایجاد/به‌روزرسانی کاربران Expert و Admin"
echo "============================================================"

# Check if Python is available
if command -v python3 &> /dev/null; then
    PYTHON_CMD=python3
elif command -v python &> /dev/null; then
    PYTHON_CMD=python
elif command -v py &> /dev/null; then
    PYTHON_CMD=py
else
    echo "❌ Python not found!"
    exit 1
fi

echo ""
echo "📋 استفاده از: $PYTHON_CMD"
echo ""

# Create/update admin user
echo "1️⃣ ایجاد/به‌روزرسانی کاربر Admin..."
$PYTHON_CMD backend/create_admin.py

echo ""
echo "2️⃣ ایجاد/به‌روزرسانی کاربر Expert..."
$PYTHON_CMD backend/seed_experts.py

echo ""
echo "============================================================"
echo "✅ عملیات کامل شد!"
echo "============================================================"
echo ""
echo "🔑 اطلاعات ورود:"
echo "   - Admin: admin / Pirooz13@!"
echo "   - Expert: expert / expert123"
echo ""
echo "💡 برای تست ورود:"
echo "   node scripts/test-login-credentials.js"
echo ""
