#!/bin/bash

# Healthcare Symptom Checker - Optimized Deployment Script
# This script optimizes the deployment for Render's memory constraints

echo "🚀 Starting optimized deployment for Healthcare Symptom Checker..."

# Set environment variables for memory optimization
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1

# Install dependencies with memory optimization
echo "📦 Installing dependencies..."
pip install --no-cache-dir -r requirements.txt

# Start the application
echo "🏥 Starting Healthcare Symptom Checker..."
python main.py
