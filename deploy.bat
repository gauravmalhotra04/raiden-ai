@echo off
echo Starting Raiden AI deployment...

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Set environment variable (you'll need to set your actual API key)
echo Setting up environment...
set GROQ_API_KEY=your_api_key_here
set FLASK_ENV=development

REM Initialize database
echo Initializing database...
python -c "from server import init_db; init_db()"

REM Start the application
echo Starting Raiden AI...
echo Access the application at: http://localhost:5000
python server.py

pause 