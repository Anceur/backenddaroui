# Image Upload Guide

## How Images Work

### Backend Configuration
- Images are stored in: `backend/media/menu_items/`
- Images are served at: `http://localhost:8000/media/menu_items/[filename]`
- The API automatically converts image paths to full absolute URLs

### Uploading Images

#### Option 1: Django Admin (Recommended)
1. Start your Django server: `python manage.py runserver`
2. Go to: `http://localhost:8000/admin/`
3. Login with admin credentials (username: `admin`, password: `admin123`)
4. Navigate to **Main > Menu items**
5. Click on a menu item to edit
6. Click **Choose File** under the Image field
7. Select your image file
8. Click **Save**

#### Option 2: Using Management Command
You can add images programmatically by modifying the seed script or creating a custom command.

### Image Requirements
- **Supported formats**: JPG, JPEG, PNG, GIF, WebP
- **Recommended size**: 800x600 pixels or similar aspect ratio
- **File size**: Keep under 5MB for best performance

### Troubleshooting

#### Images not showing in frontend:
1. **Check if image exists in database:**
   ```bash
   python manage.py shell
   >>> from main.models import MenuItem
   >>> item = MenuItem.objects.first()
   >>> print(item.image.url if item.image else "No image")
   ```

2. **Verify media files are being served:**
   - Check `backend/backend/urls.py` has media file serving configured
   - Ensure `DEBUG = True` in settings (for development)
   - Check that `MEDIA_ROOT` and `MEDIA_URL` are set correctly

3. **Check browser console:**
   - Open browser DevTools (F12)
   - Check Network tab for failed image requests
   - Look for CORS errors or 404 errors

4. **Verify image URL format:**
   - Image URLs should be: `http://localhost:8000/media/menu_items/filename.jpg`
   - Not relative paths like: `/media/menu_items/filename.jpg`

#### Common Issues:

**Issue: Image shows broken icon**
- **Solution**: Check that the file actually exists in `backend/media/menu_items/`
- Verify file permissions

**Issue: CORS error when loading images**
- **Solution**: Check `CORS_ALLOWED_ORIGINS` in `settings.py` includes your frontend URL

**Issue: 404 Not Found**
- **Solution**: 
  - Ensure Django server is running
  - Check `MEDIA_ROOT` path is correct
  - Verify `urls.py` has media file serving enabled

**Issue: Image uploads but doesn't save**
- **Solution**: 
  - Check `MEDIA_ROOT` directory exists and is writable
  - Verify file size isn't too large
  - Check Django logs for errors

### Testing Image URLs

After uploading an image, test the API:
```bash
curl http://localhost:8000/menu-items/public/
```

The response should include `image` field with full URL like:
```json
{
  "id": 1,
  "name": "Classic Burger",
  "image": "http://localhost:8000/media/menu_items/burger.jpg",
  ...
}
```

### Frontend Image Display

The frontend automatically:
- Shows the image if available
- Displays a placeholder if no image
- Handles image loading errors gracefully
- Falls back to a default placeholder on error


