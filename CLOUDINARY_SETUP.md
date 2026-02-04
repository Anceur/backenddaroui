# Cloudinary Image Storage Setup

Your project is now configured to store images in Cloudinary! 🎉

## Configuration

The following settings have been configured in `backend/backend/settings.py`:

- ✅ Cloudinary apps installed (`cloudinary`, `cloudinary_storage`)
- ✅ Cloudinary configuration with your credentials
- ✅ `DEFAULT_FILE_STORAGE` set to use Cloudinary
- ✅ Cloudinary initialized with secure HTTPS

## How It Works

1. **Image Upload**: When you upload an image through the admin panel or API, it's automatically uploaded to Cloudinary
2. **Image URLs**: Cloudinary automatically generates HTTPS URLs for your images
3. **CDN Delivery**: Images are served from Cloudinary's global CDN for fast delivery

## Your Cloudinary Credentials

Currently configured with:
- **Cloud Name**: `dn8xzjryk`
- **API Key**: `911141654755575`
- **API Secret**: `FCdYWgHG-bQS6ISbJ0J2aSSTkJk`

## Environment Variables (Optional)

You can also set these via environment variables for better security:

```bash
# Windows
set CLOUDINARY_CLOUD_NAME=dn8xzjryk
set CLOUDINARY_API_KEY=911141654755575
set CLOUDINARY_API_SECRET=FCdYWgHG-bQS6ISbJ0J2aSSTkJk

# Linux/Mac
export CLOUDINARY_CLOUD_NAME=dn8xzjryk
export CLOUDINARY_API_KEY=911141654755575
export CLOUDINARY_API_SECRET=FCdYWgHG-bQS6ISbJ0J2aSSTkJk
```

Or add to `.env` file:
```
CLOUDINARY_CLOUD_NAME=dn8xzjryk
CLOUDINARY_API_KEY=911141654755575
CLOUDINARY_API_SECRET=FCdYWgHG-bQS6ISbJ0J2aSSTkJk
```

## Testing

1. **Upload an image** through the Django admin panel or API
2. **Check the image URL** - it should be a Cloudinary URL like:
   ```
   https://res.cloudinary.com/dn8xzjryk/image/upload/v1234567890/menu_items/image.jpg
   ```
3. **Verify** the image loads correctly in your frontend

## Benefits

- ✅ **Global CDN**: Fast image delivery worldwide
- ✅ **Automatic Optimization**: Cloudinary can optimize images automatically
- ✅ **Scalability**: No storage limits on your server
- ✅ **Transformations**: Can resize, crop, and transform images on-the-fly
- ✅ **HTTPS**: All images served over secure HTTPS

## Troubleshooting

### Images not uploading to Cloudinary

1. Check that `cloudinary` and `cloudinary_storage` are in `INSTALLED_APPS`
2. Verify your Cloudinary credentials are correct
3. Check Django logs for any errors
4. Make sure `DEFAULT_FILE_STORAGE` is set correctly

### Images showing broken links

1. Verify the image was uploaded successfully to Cloudinary
2. Check the Cloudinary dashboard: https://console.cloudinary.com/
3. Ensure your Cloudinary account is active

### Want to switch back to local storage?

Comment out the Cloudinary settings and uncomment local storage:
```python
# DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"
MEDIA_ROOT = BASE_DIR / "media"
```

## Next Steps

1. Restart your Django server
2. Upload a test image through the admin panel
3. Verify the image URL is a Cloudinary URL
4. Check that images load correctly in your frontend

Your images are now stored in the cloud! ☁️



