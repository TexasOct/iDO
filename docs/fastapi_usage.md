# FastAPI Server Usage Guide

The Rewind backend now provides a unified FastAPI application for testing and development without the Tauri desktop wrapper.

## Quick Start

### Development Mode (with auto-reload)

```bash
# From project root
uvicorn app:app --reload
```

The server will start at `http://localhost:8000` with hot-reload enabled.

### Using uv run

```bash
# From project root
uv run python app.py
```

This will use configuration from `backend/config/config.toml` and start on the configured host/port.

### Production Deployment

```bash
# Standard uvicorn with gunicorn (recommended for production)
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app:app --bind 0.0.0.0:8000
```

## API Documentation

Once the server is running, you can access:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **API Endpoints**: http://localhost:8000/api/*

## Available Endpoints

### Health Check

- **GET** `/` - Root endpoint with API information
- **GET** `/health` - Health check and coordinator status

### API Handlers (Auto-registered)

All handlers decorated with `@api_handler` are automatically registered:

- **GET/POST** `/api/*` - Various system, perception, and processing endpoints

To see all available endpoints, visit the Swagger UI at `/docs`.

## Configuration

The FastAPI server uses the same configuration file as the Tauri app:

**File**: `backend/config/config.toml`

Key settings:

```toml
[server]
host = "0.0.0.0"
port = 8000
debug = true  # Set to false for production
```

## Backend Initialization

When the FastAPI server starts, it:

1. Loads configuration from `backend/config/config.toml`
2. Initializes SQLite database at configured location
3. Initializes the Settings manager
4. Initializes the Pipeline coordinator (but doesn't auto-start monitoring)

### Starting Monitoring

To start the monitoring pipeline programmatically:

```bash
# Send POST request to start system
curl -X POST http://localhost:8000/api/startSystem

# Response
{
  "success": true,
  "message": "系统已启动",
  "timestamp": "2025-10-24T22:30:00"
}
```

To stop:

```bash
curl -X POST http://localhost:8000/api/stopSystem
```

## Environment Variables

Optional environment variables:

```bash
# Enable TypeScript client generation (development only)
export PYTAURI_GEN_TS=1
uv run python app.py

# Disable debug logging
export DEBUG=0
uv run python app.py
```

## Troubleshooting

### Port Already in Use

If port 8000 is already in use:

```bash
# Use a different port
uvicorn app:app --port 8001

# Or check what's using the port
lsof -i :8000
kill -9 <PID>
```

### Database Locked

If you see "database is locked" errors:

1. Ensure only one Tauri instance or FastAPI server is running
2. Check for leftover Python processes: `ps aux | grep python`
3. Restart the backend

### Import Errors

If you get import errors:

1. Ensure you've run `uv sync` to install dependencies
2. Check that you're running from the project root
3. Verify Python path includes the backend directory

## Testing

### Using curl

```bash
# Test health check
curl http://localhost:8000/health

# Get system stats
curl http://localhost:8000/api/getSystemStats

# Start monitoring
curl -X POST http://localhost:8000/api/startSystem

# Stop monitoring
curl -X POST http://localhost:8000/api/stopSystem
```

### Using Python

```python
import httpx
import asyncio

async def test_api():
    async with httpx.AsyncClient() as client:
        # Health check
        response = await client.get('http://localhost:8000/health')
        print(response.json())

        # Get settings
        response = await client.get('http://localhost:8000/api/getSettingsInfo')
        print(response.json())

asyncio.run(test_api())
```

## Architecture

```
app.py (FastAPI entry point)
  ├─ Lifespan Management
  │   ├─ Startup: Load config, init DB, init coordinator
  │   └─ Shutdown: Stop coordinator, clean resources
  ├─ CORS Middleware
  ├─ API Routes (/api/*)
  │   └─ Auto-registered handlers from backend/handlers/
  └─ WebSocket Routes (/ws)
      └─ Real-time event streaming via ConnectionManager
```

## Files Structure After Refactoring

```
backend/
  ├─ app.py                 ← FastAPI application (REMOVED)
  ├─ websocket.py           ← WebSocket handling (MOVED from api/)
  ├─ handlers/
  │   ├─ __init__.py
  │   ├─ greeting.py
  │   ├─ perception.py
  │   ├─ processing.py
  │   ├─ system.py
  │   └─ agents.py
  ├─ core/
  │   ├─ db.py
  │   ├─ coordinator.py
  │   ├─ settings.py
  │   └─ logger.py
  └─ ...other modules

app.py (ROOT)              ← FastAPI entry point (NEW)
  └─ Uses backend modules
```

## Next Steps

- Implement API authentication (JWT, API keys)
- Add rate limiting and request validation
- Deploy to production server
- Set up monitoring and logging aggregation
