# 🚀 Healthcare Symptom Checker - Deployment Guide

This guide provides step-by-step instructions for deploying the Healthcare Symptom Checker application to various platforms.

## 📋 Prerequisites

### Required API Keys
1. **Google Gemini API Key**
   - Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Create a new API key
   - Copy the key for later use

2. **Groq API Key**
   - Go to [Groq Console](https://console.groq.com/keys)
   - Create a new API key
   - Copy the key for later use

### Required Software
- Python 3.11+
- Git
- PostgreSQL (for local development)
- Docker & Docker Compose (for containerized deployment)

## 🏠 Local Development Setup

### 1. Clone and Setup
```bash
# Clone the repository
git clone <your-repo-url>
cd Healthcare_Symptom_Checker

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration
```bash
# Copy environment template
cp .env_example .env

# Edit .env file with your API keys
nano .env  # or use your preferred editor
```

**Required .env variables:**
```bash
GEMINI_API_KEY=your_gemini_api_key_here
GROQ_API_KEY=your_groq_api_key_here
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=symptom_checker
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
DEBUG=true
```

### 3. Database Setup
```bash
# Start PostgreSQL (using Docker)
docker run --name postgres-db \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  -d postgres:15

# Create database
createdb symptom_checker
```

### 4. Run the Application
```bash
# Development mode
python main.py

# Or use the deployment script
./deploy.sh local  # Linux/Mac
deploy.bat local   # Windows
```

**Access the application:**
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/api/health

## 🐳 Docker Deployment

### Quick Start with Docker Compose
```bash
# 1. Set up environment variables
cp .env_example .env
# Edit .env with your API keys

# 2. Start all services
docker-compose up -d

# 3. Check logs
docker-compose logs -f api

# 4. Access the application
# API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Manual Docker Build
```bash
# Build the image
docker build -t healthcare-symptom-checker .

# Run the container
docker run -p 8000:8000 \
  -e GEMINI_API_KEY=your_key \
  -e GROQ_API_KEY=your_key \
  -e POSTGRES_HOST=host.docker.internal \
  healthcare-symptom-checker
```

### Docker Services
- **API**: FastAPI application (port 8000)
- **PostgreSQL**: Database (port 5432)
- **Redis**: Caching (port 6379)
- **Nginx**: Reverse proxy (port 80)

## ☁️ Cloud Deployment

### 🎯 Deploy to Render

#### Method 1: Using Render Dashboard
1. **Connect Repository**
   - Go to [Render Dashboard](https://dashboard.render.com)
   - Click "New +" → "Web Service"
   - Connect your GitHub repository

2. **Configure Web Service**
   - **Name**: `healthcare-symptom-checker`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:$PORT`

3. **Add Environment Variables**
   ```
   GEMINI_API_KEY=your_gemini_api_key
   GROQ_API_KEY=your_groq_api_key
   DEBUG=false
   LOG_LEVEL=INFO
   ```

4. **Add PostgreSQL Database**
   - Click "New +" → "PostgreSQL"
   - **Name**: `healthcare-symptom-checker-db`
   - **Plan**: Free tier
   - Copy the connection details

5. **Update Environment Variables**
   ```
   POSTGRES_HOST=your_postgres_host
   POSTGRES_PORT=5432
   POSTGRES_DB=your_database_name
   POSTGRES_USER=your_username
   POSTGRES_PASSWORD=your_password
   ```

#### Method 2: Using render.yaml
```bash
# 1. Push your code to GitHub
git add .
git commit -m "Add render.yaml configuration"
git push origin main

# 2. Connect repository to Render
# Render will automatically detect render.yaml and configure the services
```

### 🚂 Deploy to Railway

#### Method 1: Using Railway CLI
```bash
# 1. Install Railway CLI
npm install -g @railway/cli

# 2. Login to Railway
railway login

# 3. Initialize project
railway init

# 4. Set environment variables
railway variables set GEMINI_API_KEY=your_gemini_api_key
railway variables set GROQ_API_KEY=your_groq_api_key
railway variables set DEBUG=false

# 5. Add PostgreSQL
railway add postgresql

# 6. Deploy
railway up
```

#### Method 2: Using Railway Dashboard
1. **Connect Repository**
   - Go to [Railway Dashboard](https://railway.app)
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your repository

2. **Add PostgreSQL**
   - Click "New" → "Database" → "PostgreSQL"
   - Railway will automatically set `DATABASE_URL`

3. **Set Environment Variables**
   - Go to your service settings
   - Add the following variables:
     ```
     GEMINI_API_KEY=your_gemini_api_key
     GROQ_API_KEY=your_groq_api_key
     DEBUG=false
     ```

### 🟣 Deploy to Heroku

```bash
# 1. Install Heroku CLI
# Download from: https://devcenter.heroku.com/articles/heroku-cli

# 2. Login to Heroku
heroku login

# 3. Create Heroku app
heroku create your-app-name

# 4. Add PostgreSQL
heroku addons:create heroku-postgresql:hobby-dev

# 5. Set environment variables
heroku config:set GEMINI_API_KEY=your_gemini_api_key
heroku config:set GROQ_API_KEY=your_groq_api_key
heroku config:set DEBUG=false

# 6. Deploy
git push heroku main

# 7. Open the app
heroku open
```

## 🧪 Testing Deployment

### Health Check
```bash
# Test the health endpoint
curl https://your-app-url.com/api/health

# Expected response:
{
  "status": "healthy",
  "services": {
    "database": "operational",
    "rag": "operational",
    "llm": "operational"
  }
}
```

### API Testing
```bash
# Test symptom checking endpoint
curl -X POST "https://your-app-url.com/api/symptom/start" \
  -H "Content-Type: application/json" \
  -d '{
    "age": 30,
    "sex": "male",
    "medical_history": ["diabetes"],
    "medications": ["metformin"]
  }'
```

### Load Testing
```bash
# Install Apache Bench
# Ubuntu/Debian: sudo apt-get install apache2-utils
# macOS: brew install httpie

# Test with 100 requests, 10 concurrent
ab -n 100 -c 10 https://your-app-url.com/api/health
```

## 🔧 Production Configuration

### Environment Variables for Production
```bash
# API Keys
GEMINI_API_KEY=your_production_gemini_key
GROQ_API_KEY=your_production_groq_key

# Database
POSTGRES_HOST=your_production_db_host
POSTGRES_PORT=5432
POSTGRES_DB=your_production_db_name
POSTGRES_USER=your_production_db_user
POSTGRES_PASSWORD=your_production_db_password

# Application
DEBUG=false
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=8000

# Security
ALLOWED_ORIGINS=https://your-frontend-domain.com
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=3600

# LLM Configuration
GEMINI_MODEL=gemini-1.5-pro
GROQ_MODEL=llama-3.1-70b-versatile
PRIMARY_LLM=gemini
FALLBACK_LLM=groq
```

### Security Considerations
1. **HTTPS**: Always use HTTPS in production
2. **API Keys**: Store API keys securely (use environment variables)
3. **Database**: Use strong passwords and restrict access
4. **Rate Limiting**: Configure appropriate rate limits
5. **CORS**: Set proper CORS origins
6. **Logging**: Enable structured logging
7. **Monitoring**: Set up health checks and monitoring

### Performance Optimization
1. **Database Connection Pooling**: Configured in settings
2. **Caching**: Redis for session caching
3. **Load Balancing**: Use multiple workers
4. **CDN**: Use CDN for static assets
5. **Monitoring**: Set up APM tools

## 🚨 Troubleshooting

### Common Issues

#### 1. Database Connection Issues
```bash
# Check database connectivity
psql -h your_host -U your_user -d your_db -c "SELECT 1;"

# Check environment variables
echo $POSTGRES_HOST
echo $POSTGRES_USER
```

#### 2. API Key Issues
```bash
# Test API keys
curl -H "Authorization: Bearer $GEMINI_API_KEY" \
  "https://generativelanguage.googleapis.com/v1/models"

curl -H "Authorization: Bearer $GROQ_API_KEY" \
  "https://api.groq.com/openai/v1/models"
```

#### 3. Port Issues
```bash
# Check if port is in use
netstat -tulpn | grep :8000

# Kill process using port
sudo kill -9 $(lsof -t -i:8000)
```

#### 4. Docker Issues
```bash
# Check Docker status
docker ps
docker-compose ps

# View logs
docker-compose logs api
docker logs container_name

# Rebuild containers
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Log Analysis
```bash
# View application logs
tail -f logs/symptom_checker.log

# View Docker logs
docker-compose logs -f api

# View system logs
journalctl -u your-service-name -f
```

### Performance Monitoring
```bash
# Check resource usage
docker stats

# Check database performance
psql -c "SELECT * FROM pg_stat_activity;"

# Monitor API response times
curl -w "@curl-format.txt" -o /dev/null -s https://your-app-url.com/api/health
```

## 📊 Monitoring and Maintenance

### Health Monitoring
- **Endpoint**: `/api/health`
- **Frequency**: Every 30 seconds
- **Alerts**: Set up alerts for health check failures

### Log Monitoring
- **Log Level**: INFO for production
- **Rotation**: Daily log rotation
- **Retention**: 30 days

### Database Maintenance
- **Backups**: Daily automated backups
- **Monitoring**: Connection pool monitoring
- **Optimization**: Regular query optimization

### Security Monitoring
- **Rate Limiting**: Monitor rate limit violations
- **Failed Requests**: Monitor 4xx/5xx errors
- **Suspicious Activity**: Monitor for unusual patterns

## 🔄 Updates and Maintenance

### Application Updates
```bash
# Pull latest changes
git pull origin main

# Update dependencies
pip install -r requirements.txt

# Run tests
pytest

# Deploy
./deploy.sh docker  # or your preferred method
```

### Database Migrations
```bash
# Run migrations (if any)
alembic upgrade head

# Backup before migration
pg_dump your_database > backup.sql
```

### Security Updates
```bash
# Update dependencies
pip install --upgrade -r requirements.txt

# Check for vulnerabilities
safety check

# Update Docker images
docker-compose pull
docker-compose up -d
```

## 📞 Support

### Getting Help
1. **Documentation**: Check README.md and API docs
2. **Issues**: Report bugs via GitHub Issues
3. **Discussions**: Use GitHub Discussions for questions
4. **Email**: Contact the development team

### Emergency Procedures
1. **Service Down**: Check health endpoint and logs
2. **Database Issues**: Check connection and restart if needed
3. **API Key Issues**: Verify keys and regenerate if necessary
4. **High Load**: Scale up resources or enable rate limiting

---

**🎉 Congratulations! Your Healthcare Symptom Checker is now deployed and ready to help patients!**

Remember to:
- Monitor the application regularly
- Keep API keys secure
- Update dependencies regularly
- Backup your database
- Test emergency detection functionality
