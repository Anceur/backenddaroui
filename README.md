# Django Backend with Channels (WebSocket Support)

This Django project uses **Channels** for WebSocket support, which requires running the server with an ASGI server (like `daphne`) instead of the standard Django development server.

## Prerequisites

1. **Python 3.8+** installed
2. **Virtual Environment** (recommended)
3. **Redis** (optional for local development - the project falls back to InMemoryChannelLayer if Redis is not available)

## Setup Instructions

### 1. Create and Activate Virtual Environment

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 3. Database Setup

```bash
# Run migrations
python manage.py migrate

# Create superuser (optional)
python manage.py createsuperuser
```

### 4. Collect Static Files (if needed)

```bash
python manage.py collectstatic
```

## Running the Server

### Option 1: Using Daphne (Recommended for WebSocket Support)

**Windows:**
```bash
# Using the provided batch script
run_websocket_server.bat

# Or manually:
daphne -b 0.0.0.0 -p 8000 backend.asgi:application
```

**Linux/Mac:**
```bash
# Using the provided shell script
chmod +x run_websocket_server.sh
./run_websocket_server.sh

# Or manually:
daphne -b 0.0.0.0 -p 8000 backend.asgi:application
```

### Option 2: Using Uvicorn

```bash
uvicorn backend.asgi:application --host 0.0.0.0 --port 8000 --reload
```

### Option 3: Standard Django Server (WebSockets won't work)

```bash
python manage.py runserver
```

⚠️ **Note:** The standard `runserver` command will NOT support WebSocket connections. Use `daphne` or `uvicorn` for full functionality.

## Redis Setup (Optional for Local Development)

The project will work without Redis using InMemoryChannelLayer, but Redis is recommended for production and better performance.

### Install Redis (Windows)

1. Download Redis for Windows from: https://github.com/microsoftarchive/redis/releases
2. Or use WSL: `wsl sudo apt-get install redis-server`
3. Or use Docker: `docker run -d -p 6379:6379 redis`

### Install Redis (Linux/Mac)

```bash
# Ubuntu/Debian
sudo apt-get install redis-server

# Mac (using Homebrew)
brew install redis
```

### Start Redis

**Windows:**
```bash
redis-server
```

**Linux/Mac:**
```bash
redis-server
# Or as a service:
sudo systemctl start redis
```

### Configure Redis in Settings

If Redis is running locally on default port, set environment variable:
```bash
# Windows
set REDIS_URL=redis://localhost:6379/0

# Linux/Mac
export REDIS_URL=redis://localhost:6379/0
```

Or add to your `.env` file:
```
REDIS_URL=redis://localhost:6379/0
```

## Environment Variables

Create a `.env` file in the `backend` directory (optional for local development):

```env
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
REDIS_URL=redis://localhost:6379/0
```

## Access Points

- **API Base URL:** http://localhost:8000/
- **Admin Panel:** http://localhost:8000/admin/
- **WebSocket Endpoint:** ws://localhost:8000/ws/notifications/

## Troubleshooting

### Admin Panel Not Styled

If the admin panel appears without CSS:
1. Make sure static files are collected: `python manage.py collectstatic`
2. Restart the server
3. Clear browser cache (Ctrl+F5)

### WebSocket Connection Issues

1. Make sure you're using `daphne` or `uvicorn`, not `runserver`
2. Check that Channels is properly configured in `settings.py`
3. Verify Redis is running (if using Redis)

### Port Already in Use

If port 8000 is already in use:
```bash
# Use a different port
daphne -b 0.0.0.0 -p 8001 backend.asgi:application
```

## Development vs Production

- **Development:** Uses InMemoryChannelLayer if Redis is not available
- **Production:** Requires Redis for proper WebSocket support and scalability

## Additional Commands

```bash
# Create database migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Run Django shell
python manage.py shell

# Check for issues
python manage.py check
```




