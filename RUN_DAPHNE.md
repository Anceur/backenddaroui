# How to Run the Project with Daphne

This project uses **Daphne** (ASGI server) to support WebSockets and Django Channels.

## Quick Start

### Step 1: Install Dependencies

Make sure you're in the `backend` directory and have a virtual environment activated:

```bash
cd backend
pip install -r requirements.txt
```

This will install `daphne==4.0.0` along with all other dependencies.

### Step 2: Run with Daphne

**Option A: Using the Batch Script (Windows)**
```bash
run_websocket_server.bat
```

**Option B: Manual Command**
```bash
daphne -b 0.0.0.0 -p 8000 backend.asgi:application
```

**Option C: With Auto-reload (Development)**
```bash
daphne -b 0.0.0.0 -p 8000 backend.asgi:application --verbosity 2
```

## Command Breakdown

- `daphne` - The ASGI server command
- `-b 0.0.0.0` - Bind to all network interfaces (allows external connections)
- `-p 8000` - Port number (default: 8000)
- `backend.asgi:application` - Path to your ASGI application

## Alternative: Using Uvicorn

If you prefer Uvicorn (another ASGI server):

```bash
uvicorn backend.asgi:application --host 0.0.0.0 --port 8000 --reload
```

The `--reload` flag enables auto-reload on code changes (useful for development).

## Verify It's Running

Once started, you should see:
```
Starting server at tcp:port=8000:interface=0.0.0.0
```

Access your application at:
- **API:** http://localhost:8000/
- **Admin:** http://localhost:8000/admin/
- **WebSocket:** ws://localhost:8000/ws/notifications/

## Troubleshooting

### Port Already in Use

If port 8000 is busy, use a different port:
```bash
daphne -b 0.0.0.0 -p 8001 backend.asgi:application
```

### Daphne Not Found

If you get "daphne: command not found":
```bash
# Make sure you're in the virtual environment
pip install daphne

# Or install from requirements
pip install -r requirements.txt
```

### WebSocket Not Working

1. Make sure you're using `daphne`, not `python manage.py runserver`
2. Check that Channels is properly configured
3. Verify Redis is running (if using Redis for production)

## Production vs Development

**Development:**
```bash
daphne -b 0.0.0.0 -p 8000 backend.asgi:application
```

**Production (with more workers):**
```bash
daphne -b 0.0.0.0 -p 8000 backend.asgi:application --workers 4
```

## Stop the Server

Press `Ctrl+C` in the terminal to stop the server.




