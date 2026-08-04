@echo off
echo Shared user setup is retired. Starting interactive administrator onboarding.
python manage.py create-admin
exit /b %ERRORLEVEL%
