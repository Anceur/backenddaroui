# WebSocket Token Endpoint Fix

## Issue
The `/websocket-token/` endpoint returns a 404 error when accessed from the frontend.

## Analysis

### Current Setup
1. **View**: `backend/main/views_websocket.py` - `WebSocketTokenView`
   - ✅ Properly defined
   - ✅ Uses `IsAuthenticated` permission
   - ✅ Generates fresh JWT token for authenticated users
   - ✅ Includes error handling and logging

2. **URL Registration**: `backend/main/urls.py` line 124
   - ✅ Endpoint registered: `path('websocket-token/', WebSocketTokenView.as_view(), name='websocket_token')`
   - ✅ Import statement: `from .views_websocket import WebSocketTokenView`

3. **Main URL Configuration**: `backend/backend/urls.py`
   - ✅ Includes `main.urls` at root: `path('', include(main.urls))`
   - ✅ Endpoint should be accessible at: `http://localhost:8000/websocket-token/`

4. **Django Settings**: `backend/backend/settings.py`
   - ✅ `channels` in `INSTALLED_APPS`
   - ✅ `ASGI_APPLICATION` configured
   - ✅ `CHANNEL_LAYERS` configured
   - ✅ `REST_FRAMEWORK` configured

## Root Cause
The 404 error is most likely due to:
1. **Server not restarted** after adding the endpoint
2. **Caching** of old URL patterns
3. **Server running with wrong command** (using `runserver` instead of `daphne`)

## Solution

### Step 1: Restart the Server
**IMPORTANT**: The server MUST be restarted after adding new endpoints.

**Stop the current server** (Ctrl+C) and restart with:
```bash
cd backend
daphne -b 0.0.0.0 -p 8000 backend.asgi:application
```

**OR** if using the batch script:
```bash
cd backend
.\run_websocket_server.bat
```

### Step 2: Verify Endpoint is Accessible
After restarting, test the endpoint:

```bash
# Using curl (replace YOUR_ACCESS_TOKEN with actual token)
curl -X GET http://localhost:8000/websocket-token/ \
  -H "Cookie: access_token=YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json"
```

Or test in browser console (after logging in):
```javascript
fetch('http://localhost:8000/websocket-token/', {
  credentials: 'include'
})
.then(r => r.json())
.then(console.log)
```

### Step 3: Check Server Logs
When the frontend calls the endpoint, you should see in the daphne logs:
```
HTTP GET /websocket-token/ 200 OK
```

If you see `404`, the server wasn't restarted or there's a routing issue.

## Verification Checklist

- [ ] Server restarted with `daphne` (not `runserver`)
- [ ] Endpoint accessible at `http://localhost:8000/websocket-token/`
- [ ] User is authenticated (has valid JWT token in cookies)
- [ ] CORS settings allow requests from frontend
- [ ] No import errors in Django logs
- [ ] URL pattern correctly registered in `main/urls.py`

## Expected Behavior

### Successful Response (200 OK):
```json
{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

### Error Responses:
- **401 Unauthorized**: User not authenticated (need to log in)
- **500 Internal Server Error**: Server error (check logs)
- **404 Not Found**: Endpoint not found (server needs restart or routing issue)

## Frontend Integration

The frontend already handles 404 gracefully:
- `frontend/src/shared/api/websocket-token.ts` catches 404 and logs a warning
- WebSocket will still attempt to connect (using cookies if available)
- Backend middleware can authenticate via cookies, headers, or query string

## Additional Notes

1. **Token Generation**: The view now generates a fresh token instead of reading from cookies, which is more reliable.

2. **Error Handling**: Comprehensive error handling and logging added to help debug issues.

3. **Authentication**: The endpoint requires authentication (`IsAuthenticated`), so ensure the user is logged in before calling it.

4. **WebSocket Fallback**: Even if the token endpoint fails, WebSocket authentication can still work via:
   - Cookies (sent automatically by browser)
   - Query string (if token is provided)
   - Headers (if configured)

## Troubleshooting

If the endpoint still returns 404 after restarting:

1. **Check URL patterns**:
   ```bash
   cd backend
   python manage.py show_urls | grep websocket
   ```

2. **Check for import errors**:
   ```bash
   cd backend
   python manage.py check
   ```

3. **Verify view is importable**:
   ```python
   python manage.py shell
   >>> from main.views_websocket import WebSocketTokenView
   >>> print(WebSocketTokenView)
   ```

4. **Check server logs** for any errors during startup

5. **Clear Python cache** (if needed):
   ```bash
   find backend -type d -name __pycache__ -exec rm -r {} +
   find backend -name "*.pyc" -delete
   ```

