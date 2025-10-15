@echo off
REM Healthcare Symptom Checker Deployment Script for Windows
REM Supports multiple deployment targets: local, docker, render, railway

setlocal enabledelayedexpansion

REM Colors (Windows doesn't support colors in batch, but we can use echo)
set "INFO=[INFO]"
set "SUCCESS=[SUCCESS]"
set "WARNING=[WARNING]"
set "ERROR=[ERROR]"

REM Function to print status
:print_status
echo %INFO% %~1
goto :eof

:print_success
echo %SUCCESS% %~1
goto :eof

:print_warning
echo %WARNING% %~1
goto :eof

:print_error
echo %ERROR% %~1
goto :eof

REM Function to check if command exists
:command_exists
where %1 >nul 2>&1
if %errorlevel% == 0 (
    exit /b 0
) else (
    exit /b 1
)

REM Function to check environment variables
:check_env_vars
call :print_status "Checking environment variables..."

if not exist ".env" (
    call :print_warning ".env file not found. Creating from template..."
    copy .env_example .env
    call :print_warning "Please edit .env file with your API keys before continuing."
    exit /b 1
)

REM Check for required environment variables
for /f "tokens=1,2 delims==" %%a in (.env) do (
    if "%%a"=="GEMINI_API_KEY" set GEMINI_API_KEY=%%b
    if "%%a"=="GROQ_API_KEY" set GROQ_API_KEY=%%b
)

if "%GEMINI_API_KEY%"=="" (
    call :print_error "GEMINI_API_KEY not set in .env file"
    exit /b 1
)

if "%GROQ_API_KEY%"=="" (
    call :print_error "GROQ_API_KEY not set in .env file"
    exit /b 1
)

call :print_success "Environment variables validated"
goto :eof

REM Function to install dependencies
:install_dependencies
call :print_status "Installing Python dependencies..."

if not exist "venv" (
    call :print_status "Creating virtual environment..."
    python -m venv venv
)

call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

call :print_success "Dependencies installed"
goto :eof

REM Function to setup database
:setup_database
call :print_status "Setting up database..."

call :command_exists psql
if %errorlevel% == 0 (
    call :print_status "PostgreSQL client found"
    call :print_status "Please ensure PostgreSQL is running and create database 'symptom_checker'"
) else (
    call :print_warning "PostgreSQL client not found. Please install PostgreSQL."
)

call :print_success "Database setup complete"
goto :eof

REM Function to run tests
:run_tests
call :print_status "Running tests..."

call venv\Scripts\activate.bat
pytest tests/ -v --tb=short

call :print_success "Tests completed"
goto :eof

REM Function for local deployment
:deploy_local
call :print_status "Deploying locally..."

call :check_env_vars
if %errorlevel% neq 0 exit /b 1

call :install_dependencies
if %errorlevel% neq 0 exit /b 1

call :setup_database
if %errorlevel% neq 0 exit /b 1

call :print_status "Starting application..."
call venv\Scripts\activate.bat
python main.py
goto :eof

REM Function for Docker deployment
:deploy_docker
call :print_status "Deploying with Docker..."

call :command_exists docker
if %errorlevel% neq 0 (
    call :print_error "Docker not installed. Please install Docker Desktop first."
    exit /b 1
)

call :command_exists docker-compose
if %errorlevel% neq 0 (
    call :print_error "Docker Compose not installed. Please install Docker Compose first."
    exit /b 1
)

call :check_env_vars
if %errorlevel% neq 0 exit /b 1

call :print_status "Building Docker images..."
docker-compose build

call :print_status "Starting services..."
docker-compose up -d

call :print_success "Docker deployment complete"
call :print_status "Application available at: http://localhost:8000"
call :print_status "API docs available at: http://localhost:8000/docs"

call :print_status "To view logs: docker-compose logs -f api"
call :print_status "To stop services: docker-compose down"
goto :eof

REM Function for Render deployment
:deploy_render
call :print_status "Preparing for Render deployment..."

if not exist "render.yaml" (
    call :print_error "render.yaml not found"
    exit /b 1
)

call :print_success "Ready for Render deployment"
call :print_status "Next steps:"
call :print_status "1. Push your code to GitHub"
call :print_status "2. Connect your repository to Render"
call :print_status "3. Use the render.yaml configuration"
call :print_status "4. Set environment variables in Render dashboard"
goto :eof

REM Function for Railway deployment
:deploy_railway
call :print_status "Preparing for Railway deployment..."

call :command_exists railway
if %errorlevel% neq 0 (
    call :print_error "Railway CLI not installed. Please install it first:"
    call :print_status "npm install -g @railway/cli"
    exit /b 1
)

call :print_status "Logging into Railway..."
railway login

call :print_status "Initializing Railway project..."
railway init

call :print_status "Setting environment variables..."
railway variables set GEMINI_API_KEY=%GEMINI_API_KEY%
railway variables set GROQ_API_KEY=%GROQ_API_KEY%
railway variables set DEBUG=false

call :print_status "Deploying to Railway..."
railway up

call :print_success "Railway deployment complete"
goto :eof

REM Function to show help
:show_help
echo Healthcare Symptom Checker Deployment Script
echo.
echo Usage: %0 [COMMAND]
echo.
echo Commands:
echo   local     Deploy locally with Python
echo   docker    Deploy with Docker Compose
echo   render    Prepare for Render deployment
echo   railway   Deploy to Railway
echo   test      Run tests only
echo   setup     Setup development environment
echo   help      Show this help message
echo.
echo Examples:
echo   %0 local      # Run locally
echo   %0 docker     # Run with Docker
echo   %0 test       # Run tests
echo   %0 setup      # Setup development environment
goto :eof

REM Function to setup development environment
:setup_dev
call :print_status "Setting up development environment..."

call :check_env_vars
if %errorlevel% neq 0 exit /b 1

call :install_dependencies
if %errorlevel% neq 0 exit /b 1

call :setup_database
if %errorlevel% neq 0 exit /b 1

call :print_status "Installing development dependencies..."
call venv\Scripts\activate.bat
pip install pytest pytest-cov black flake8 mypy pre-commit

call :print_status "Setting up pre-commit hooks..."
pre-commit install

call :print_status "Running initial tests..."
pytest tests/ -v

call :print_success "Development environment setup complete"
call :print_status "To activate the environment: venv\Scripts\activate.bat"
goto :eof

REM Main script logic
if "%1"=="" goto show_help
if "%1"=="local" goto deploy_local
if "%1"=="docker" goto deploy_docker
if "%1"=="render" goto deploy_render
if "%1"=="railway" goto deploy_railway
if "%1"=="test" goto run_tests
if "%1"=="setup" goto setup_dev
if "%1"=="help" goto show_help
if "%1"=="--help" goto show_help
if "%1"=="-h" goto show_help

call :print_error "Unknown command: %1"
goto show_help
