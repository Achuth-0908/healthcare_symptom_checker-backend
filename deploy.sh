#!/bin/bash

# Healthcare Symptom Checker Deployment Script
# Supports multiple deployment targets: local, docker, render, railway

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check environment variables
check_env_vars() {
    print_status "Checking environment variables..."
    
    if [ ! -f ".env" ]; then
        print_warning ".env file not found. Creating from template..."
        cp .env_example .env
        print_warning "Please edit .env file with your API keys before continuing."
        exit 1
    fi
    
    # Check for required environment variables
    source .env
    
    if [ -z "$GEMINI_API_KEY" ]; then
        print_error "GEMINI_API_KEY not set in .env file"
        exit 1
    fi
    
    if [ -z "$GROQ_API_KEY" ]; then
        print_error "GROQ_API_KEY not set in .env file"
        exit 1
    fi
    
    print_success "Environment variables validated"
}

# Function to install dependencies
install_dependencies() {
    print_status "Installing Python dependencies..."
    
    if [ ! -d "venv" ]; then
        print_status "Creating virtual environment..."
        python -m venv venv
    fi
    
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    
    print_success "Dependencies installed"
}

# Function to setup database
setup_database() {
    print_status "Setting up database..."
    
    # Check if PostgreSQL is running
    if command_exists psql; then
        # Try to connect to PostgreSQL
        if psql -h localhost -U postgres -d postgres -c '\q' 2>/dev/null; then
            print_status "Creating database..."
            psql -h localhost -U postgres -d postgres -c "CREATE DATABASE symptom_checker;" 2>/dev/null || true
            print_success "Database setup complete"
        else
            print_warning "PostgreSQL not accessible. Please ensure PostgreSQL is running."
        fi
    else
        print_warning "PostgreSQL client not found. Please install PostgreSQL."
    fi
}

# Function to run tests
run_tests() {
    print_status "Running tests..."
    
    source venv/bin/activate
    pytest tests/ -v --tb=short
    
    print_success "Tests completed"
}

# Function for local deployment
deploy_local() {
    print_status "Deploying locally..."
    
    check_env_vars
    install_dependencies
    setup_database
    
    print_status "Starting application..."
    source venv/bin/activate
    python main.py
}

# Function for Docker deployment
deploy_docker() {
    print_status "Deploying with Docker..."
    
    if ! command_exists docker; then
        print_error "Docker not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command_exists docker-compose; then
        print_error "Docker Compose not installed. Please install Docker Compose first."
        exit 1
    fi
    
    check_env_vars
    
    print_status "Building Docker images..."
    docker-compose build
    
    print_status "Starting services..."
    docker-compose up -d
    
    print_success "Docker deployment complete"
    print_status "Application available at: http://localhost:8000"
    print_status "API docs available at: http://localhost:8000/docs"
    
    print_status "To view logs: docker-compose logs -f api"
    print_status "To stop services: docker-compose down"
}

# Function for Render deployment
deploy_render() {
    print_status "Preparing for Render deployment..."
    
    if [ ! -f "render.yaml" ]; then
        print_error "render.yaml not found"
        exit 1
    fi
    
    print_status "Checking Git status..."
    if [ -n "$(git status --porcelain)" ]; then
        print_warning "Uncommitted changes detected. Please commit or stash them."
        git status --short
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    print_success "Ready for Render deployment"
    print_status "Next steps:"
    print_status "1. Push your code to GitHub"
    print_status "2. Connect your repository to Render"
    print_status "3. Use the render.yaml configuration"
    print_status "4. Set environment variables in Render dashboard"
}

# Function for Railway deployment
deploy_railway() {
    print_status "Preparing for Railway deployment..."
    
    if ! command_exists railway; then
        print_error "Railway CLI not installed. Please install it first:"
        print_status "npm install -g @railway/cli"
        exit 1
    fi
    
    print_status "Logging into Railway..."
    railway login
    
    print_status "Initializing Railway project..."
    railway init
    
    print_status "Setting environment variables..."
    railway variables set GEMINI_API_KEY="$GEMINI_API_KEY"
    railway variables set GROQ_API_KEY="$GROQ_API_KEY"
    railway variables set DEBUG=false
    
    print_status "Deploying to Railway..."
    railway up
    
    print_success "Railway deployment complete"
}

# Function to show help
show_help() {
    echo "Healthcare Symptom Checker Deployment Script"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  local     Deploy locally with Python"
    echo "  docker    Deploy with Docker Compose"
    echo "  render    Prepare for Render deployment"
    echo "  railway   Deploy to Railway"
    echo "  test      Run tests only"
    echo "  setup     Setup development environment"
    echo "  help      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 local      # Run locally"
    echo "  $0 docker     # Run with Docker"
    echo "  $0 test       # Run tests"
    echo "  $0 setup      # Setup development environment"
}

# Function to setup development environment
setup_dev() {
    print_status "Setting up development environment..."
    
    check_env_vars
    install_dependencies
    setup_database
    
    print_status "Installing development dependencies..."
    source venv/bin/activate
    pip install pytest pytest-cov black flake8 mypy pre-commit
    
    print_status "Setting up pre-commit hooks..."
    pre-commit install
    
    print_status "Running initial tests..."
    pytest tests/ -v
    
    print_success "Development environment setup complete"
    print_status "To activate the environment: source venv/bin/activate"
}

# Main script logic
case "${1:-help}" in
    local)
        deploy_local
        ;;
    docker)
        deploy_docker
        ;;
    render)
        deploy_render
        ;;
    railway)
        deploy_railway
        ;;
    test)
        run_tests
        ;;
    setup)
        setup_dev
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
