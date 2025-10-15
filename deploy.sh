#!/bin/bash
# Healthcare Symptom Checker - Render Deployment Script

echo "Starting Healthcare Symptom Checker deployment..."

# Install CPU-only PyTorch first
echo "Installing CPU-only PyTorch..."
pip install torch==2.0.1+cpu torchvision==0.15.2+cpu torchaudio==2.0.2+cpu --index-url https://download.pytorch.org/whl/cpu

# Install other dependencies
echo "Installing other dependencies..."
pip install -r requirements-deploy.txt

# Run the application
echo "Starting application..."
python main.py