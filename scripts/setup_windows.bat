@echo off
REM Windows Setup Script for Condominios Manager
REM This script helps resolve pip PATH issues and install dependencies

echo ==========================================
echo Condominios Manager - Windows Setup
echo ==========================================
echo.

REM Check if Python is available
py --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python from https://www.python.org/downloads/
    exit /b 1
)

echo Python found:
py --version
echo.

REM Check if we're in a virtual environment
if defined VIRTUAL_ENV (
    echo Virtual environment active: %VIRTUAL_ENV%
    echo.
) else (
    echo No virtual environment detected.
    echo.

    REM Check if venv exists
    if exist "venv\Scripts\activate.bat" (
        echo Found existing virtual environment. Activating...
        call venv\Scripts\activate.bat
    ) else (
        echo Creating virtual environment...
        py -m venv venv
        if errorlevel 1 (
            echo ERROR: Failed to create virtual environment.
            exit /b 1
        )
        echo Virtual environment created. Activating...
        call venv\Scripts\activate.bat
    )
    echo.
)

REM Upgrade pip first
echo Upgrading pip...
py -m pip install --upgrade pip
if errorlevel 1 (
    echo WARNING: Failed to upgrade pip, continuing anyway...
)
echo.

REM Install dependencies
echo Installing production dependencies...
py -m pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install production dependencies.
    echo Check the error messages above for details.
    exit /b 1
)
echo.

REM Check if dev dependencies should be installed
set /p INSTALL_DEV="Install development dependencies? (y/n): "
if /i "%INSTALL_DEV%"=="y" (
    echo Installing development dependencies...
    py -m pip install -r requirements-dev.txt
    if errorlevel 1 (
        echo ERROR: Failed to install development dependencies.
        exit /b 1
    )
)
echo.

echo ==========================================
echo Setup completed successfully!
echo ==========================================
echo.
echo To activate the virtual environment in the future, run:
echo   venv\Scripts\activate.bat
echo.
echo Or use 'py -m pip' instead of 'pip' directly.
echo.

pause
