# backend/firebase_config.py

import firebase_admin
from firebase_admin import credentials, storage
from decouple import config

def initialize_firebase():
    """Initialize Firebase Admin SDK"""
    if not firebase_admin._apps:
        try:
            cred = credentials.Certificate({
                "type": "service_account",
                "project_id": config('FIREBASE_PROJECT_ID'),
                "private_key": config('FIREBASE_PRIVATE_KEY').replace('\\n', '\n'),
                "client_email": config('FIREBASE_CLIENT_EMAIL'),
                "token_uri": "https://oauth2.googleapis.com/token",
            })
            
            firebase_admin.initialize_app(cred, {
                'storageBucket': f"{config('FIREBASE_PROJECT_ID')}.appspot.com"
            })
            
            print("✅ Firebase Admin initialized successfully")
            
        except Exception as e:
            print(f"❌ Error initializing Firebase: {e}")
            raise


initialize_firebase()

def get_storage_bucket():
    """Get Firebase Storage bucket"""
    return storage.bucket()