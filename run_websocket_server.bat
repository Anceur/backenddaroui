@echo off
echo ========================================
echo Starting Django Server with WebSocket Support
echo ========================================
echo.
echo Make sure you have installed:
echo   pip install daphne channels
echo.
echo Starting server on http://localhost:8000
echo Press Ctrl+C to stop
echo.
daphne -b 0.0.0.0 -p 8000 backend.asgi:application

