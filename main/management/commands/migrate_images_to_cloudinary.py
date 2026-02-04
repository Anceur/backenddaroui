"""
Django management command to migrate existing local images to Cloudinary
Usage: python manage.py migrate_images_to_cloudinary
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from main.models import MenuItem, Profile
import cloudinary.uploader
import os
from pathlib import Path


class Command(BaseCommand):
    help = 'Migrates existing local images to Cloudinary'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be migrated without actually uploading',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        self.stdout.write("=" * 60)
        self.stdout.write("Migrating Images to Cloudinary")
        self.stdout.write("=" * 60)
        
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No images will be uploaded"))
        
        # Check if MEDIA_ROOT exists
        media_root = getattr(settings, 'MEDIA_ROOT', None)
        if not media_root:
            self.stdout.write(self.style.WARNING("MEDIA_ROOT not set. Checking default location..."))
            media_root = Path(settings.BASE_DIR) / "media"
        
        if not os.path.exists(media_root):
            self.stdout.write(self.style.WARNING(f"Media directory not found: {media_root}"))
            self.stdout.write("No local images to migrate.")
            return
        
        self.stdout.write(f"\nMedia root: {media_root}")
        
        # Migrate MenuItem images
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("Migrating MenuItem Images")
        self.stdout.write("=" * 60)
        
        menu_items = MenuItem.objects.exclude(image__isnull=True).exclude(image='')
        migrated_count = 0
        skipped_count = 0
        error_count = 0
        
        for item in menu_items:
            if not item.image:
                continue
            
            # Check if image is already a Cloudinary URL
            if hasattr(item.image, 'url') and ('cloudinary.com' in str(item.image.url) or item.image.url.startswith('http')):
                self.stdout.write(f"  ⏭️  Skipping {item.name} - already using Cloudinary")
                skipped_count += 1
                continue
            
            # Get local file path
            image_path = item.image.path if hasattr(item.image, 'path') else None
            
            if not image_path or not os.path.exists(image_path):
                self.stdout.write(self.style.WARNING(f"  ⚠️  {item.name}: Image file not found at {image_path}"))
                error_count += 1
                continue
            
            try:
                if dry_run:
                    self.stdout.write(f"  📋 Would upload: {item.name} -> {image_path}")
                else:
                    # Upload to Cloudinary
                    self.stdout.write(f"  📤 Uploading: {item.name}...")
                    result = cloudinary.uploader.upload(
                        image_path,
                        folder="menu_items",
                        public_id=f"menu_item_{item.id}",
                        overwrite=True
                    )
                    
                    # Update the model - CloudinaryField will handle the URL
                    item.image = result['secure_url']
                    item.save()
                    
                    self.stdout.write(self.style.SUCCESS(f"  ✅ Uploaded: {item.name}"))
                    migrated_count += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ❌ Error uploading {item.name}: {e}"))
                error_count += 1
        
        # Migrate Profile images
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("Migrating Profile Images")
        self.stdout.write("=" * 60)
        
        profiles = Profile.objects.exclude(image__isnull=True).exclude(image='')
        profile_migrated = 0
        profile_skipped = 0
        profile_errors = 0
        
        for profile in profiles:
            if not profile.image:
                continue
            
            # Check if image is already a Cloudinary URL
            if hasattr(profile.image, 'url') and ('cloudinary.com' in str(profile.image.url) or profile.image.url.startswith('http')):
                self.stdout.write(f"  ⏭️  Skipping {profile.user.username} - already using Cloudinary")
                profile_skipped += 1
                continue
            
            # Get local file path
            image_path = profile.image.path if hasattr(profile.image, 'path') else None
            
            if not image_path or not os.path.exists(image_path):
                self.stdout.write(self.style.WARNING(f"  ⚠️  {profile.user.username}: Image file not found"))
                profile_errors += 1
                continue
            
            try:
                if dry_run:
                    self.stdout.write(f"  📋 Would upload: {profile.user.username} -> {image_path}")
                else:
                    # Upload to Cloudinary
                    self.stdout.write(f"  📤 Uploading: {profile.user.username}...")
                    result = cloudinary.uploader.upload(
                        image_path,
                        folder="profiles",
                        public_id=f"profile_{profile.user.id}",
                        overwrite=True
                    )
                    
                    # Update the model
                    profile.image = result['secure_url']
                    profile.save()
                    
                    self.stdout.write(self.style.SUCCESS(f"  ✅ Uploaded: {profile.user.username}"))
                    profile_migrated += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ❌ Error uploading {profile.user.username}: {e}"))
                profile_errors += 1
        
        # Summary
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("Migration Summary")
        self.stdout.write("=" * 60)
        self.stdout.write(f"Menu Items:")
        self.stdout.write(f"  ✅ Migrated: {migrated_count}")
        self.stdout.write(f"  ⏭️  Skipped: {skipped_count}")
        self.stdout.write(f"  ❌ Errors: {error_count}")
        self.stdout.write(f"\nProfiles:")
        self.stdout.write(f"  ✅ Migrated: {profile_migrated}")
        self.stdout.write(f"  ⏭️  Skipped: {profile_skipped}")
        self.stdout.write(f"  ❌ Errors: {profile_errors}")
        self.stdout.write("=" * 60)
        
        if dry_run:
            self.stdout.write(self.style.WARNING("\nThis was a dry run. Run without --dry-run to actually migrate images."))
        else:
            self.stdout.write(self.style.SUCCESS("\n✅ Migration complete!"))



