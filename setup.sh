#!/bin/bash

# Healthcare Symptom Checker - Automated Setup Script
# This script sets up the entire application automatically

set -e  # Exit on error

echo "=========================================="
echo "Healthcare Symptom Checker Setup"
echo "=========================================="
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}➜ $1${NC}"
}

# Check Python version
print_info "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed. Please install Python 3.11 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d" " -f2 | cut -d"." -f1,2)
REQUIRED_VERSION="3.11"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    print_error "Python $REQUIRED_VERSION or higher is required. You have Python $PYTHON_VERSION"
    exit 1
fi

print_success "Python $PYTHON_VERSION detected"

# Create directory structure
print_info "Creating directory structure..."
mkdir -p backend/app/{routers,services,utils,data}
mkdir -p backend/tests
mkdir -p frontend/{css,js,assets}
mkdir -p chroma_db
mkdir -p logs

print_success "Directory structure created"

# Create and activate virtual environment
print_info "Creating virtual environment..."
cd backend
if [ ! -d "venv" ]; then
    python3 -m venv venv
    print_success "Virtual environment created"
else
    print_info "Virtual environment already exists"
fi

# Activate virtual environment
print_info "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
print_info "Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1
print_success "Pip upgraded"

# Install requirements
print_info "Installing Python dependencies..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt > /dev/null 2>&1
    print_success "Dependencies installed"
else
    print_error "requirements.txt not found"
    exit 1
fi

# Setup environment variables
print_info "Setting up environment variables..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        print_success "Created .env file from template"
        echo ""
        print_info "⚠️  IMPORTANT: Please edit .env file and add your API keys:"
        echo "   - GEMINI_API_KEY (get from https://makersuite.google.com/app/apikey)"
        echo "   - GROQ_API_KEY (get from https://console.groq.com)"
        echo ""
    else
        print_error ".env.example not found"
        exit 1
    fi
else
    print_info ".env file already exists"
fi

# Check if API keys are set
if grep -q "your_gemini_api_key_here" .env || grep -q "your_groq_api_key_here" .env; then
    print_error "Please add your actual API keys to the .env file before continuing"
    echo ""
    echo "Edit the .env file and replace:"
    echo "  - your_gemini_api_key_here"
    echo "  - your_groq_api_key_here"
    echo ""
    echo "Then run this script again."
    exit 1
fi

# Create __init__.py files
print_info "Creating Python package files..."
touch app/__init__.py
touch app/routers/__init__.py
touch app/services/__init__.py
touch app/utils/__init__.py
touch tests/__init__.py
print_success "Package files created"

# Initialize database
print_info "Initializing database..."
python3 -c "from app.database import init_db; init_db()" 2>/dev/null || print_error "Database initialization failed (this is normal if files are not in place yet)"

# Test API keys
print_info "Testing API keys..."
python3 << EOF
import os
from dotenv import load_dotenv

load_dotenv()

gemini_key = os.getenv('GEMINI_API_KEY')
groq_key = os.getenv('GROQ_API_KEY')

if gemini_key and gemini_key != 'your_gemini_api_key_here':
    print("✓ Gemini API key found")
else:
    print("✗ Gemini API key not set")

if groq_key and groq_key != 'your_groq_api_key_here':
    print("✓ Groq API key found")
else:
    print("✗ Groq API key not set")
EOF

# Create basic frontend files if they don't exist
print_info "Setting up frontend..."
cd ../frontend

if [ ! -f "index.html" ]; then
    cat > index.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Healthcare Symptom Checker</title>
    <link rel="stylesheet" href="css/styles.css">
</head>
<body>
    <div class="container">
        <header>
            <h1>🏥 Healthcare Symptom Checker</h1>
            <p>AI-powered symptom analysis - For educational purposes only</p>
        </header>
        
        <main id="app">
            <div class="disclaimer">
                <strong>⚠️ Medical Disclaimer:</strong> This is NOT a substitute for professional medical advice. 
                Always consult a healthcare provider for medical concerns.
            </div>
            
            <div id="chat-container">
                <!-- Chat messages will appear here -->
            </div>
            
            <div id="input-container">
                <textarea id="symptom-input" placeholder="Describe your symptoms..." rows="3"></textarea>
                <button id="send-button">Send</button>
            </div>
        </main>
    </div>
    
    <script src="js/app.js"></script>
</body>
</html>
EOF
    print_success "Created index.html"
fi

cd ..

# Final instructions
echo ""
echo "=========================================="
print_success "Setup completed successfully!"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Start the backend server:"
echo "   cd backend"
echo "   source venv/bin/activate"
echo "   uvicorn app.main:app --reload"
echo ""
echo "2. Access the application:"
echo "   - API: http://localhost:8000"
echo "   - Docs: http://localhost:8000/docs"
echo "   - Frontend: Open frontend/index.html in browser"
echo ""
echo "3. Or use Docker:"
echo "   docker-compose up --build"
echo ""
echo "For detailed instructions, see README.md"
echo ""
print_info "Happy coding! 🚀"