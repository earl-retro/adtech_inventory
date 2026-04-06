@echo off
title adTech - Start Server
echo.
echo  ==========================================
echo   adTech Computer Sales ^& Services IMS
echo   Starting Django Backend Server...
echo  ==========================================
echo.
cd /d "%~dp0"
echo  [1/2] Running server on http://127.0.0.1:8000
echo  [2/2] Open frontend\login.html in your browser
echo.
echo  Admin credentials: admin / admin123
echo  Django Admin: http://127.0.0.1:8000/admin/
echo.
python manage.py runserver
pause
