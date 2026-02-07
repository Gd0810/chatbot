@echo off
echo Activating virtual environment...
call env\Scripts\activate.bat

echo.
echo Running API key diagnostic test...
python test_api_key_debug.py

echo.
echo Press any key to exit...
pause >nul
