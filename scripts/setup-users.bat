@echo off
REM Setup Users Script for Windows
REM Creates/updates admin and expert users

echo ============================================================
echo 🔧 ایجاد/به‌روزرسانی کاربران Expert و Admin
echo ============================================================

REM Check if Python is available
where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    set PYTHON_CMD=python
) else (
    where py >nul 2>nul
    if %ERRORLEVEL% EQU 0 (
        set PYTHON_CMD=py
    ) else (
        echo ❌ Python not found!
        exit /b 1
    )
)

echo.
echo 📋 استفاده از: %PYTHON_CMD%
echo.

REM Create/update admin user
echo 1️⃣ ایجاد/به‌روزرسانی کاربر Admin...
%PYTHON_CMD% backend\create_admin.py

echo.
echo 2️⃣ ایجاد/به‌روزرسانی کاربر Expert...
%PYTHON_CMD% backend\seed_experts.py

echo.
echo ============================================================
echo ✅ عملیات کامل شد!
echo ============================================================
echo.
echo 🔑 اطلاعات ورود:
echo    - Admin: admin / Pirooz13@!
echo    - Expert: expert / expert123
echo.
echo 💡 برای تست ورود:
echo    node scripts\test-login-credentials.js
echo.
