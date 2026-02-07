import os
import json
import firebase_admin
from firebase_admin import credentials, storage

def initialize_firebase():
    """Initialize Firebase Admin SDK if not already initialized"""
    if not firebase_admin._apps:
        try:
            # جلب بيانات الخدمة من متغير البيئة
            service_account_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT")
            if not service_account_json:
                raise ValueError("FIREBASE_SERVICE_ACCOUNT environment variable not set")
            
            cred = credentials.Certificate(json.loads(service_account_json))
            firebase_admin.initialize_app(cred, {
              "storageBucket": "daroui.firebasestorage.app" 
            })
            print("✅ Firebase initialized successfully")
        except Exception as e:
            print(f"❌ Error initializing Firebase: {e}")
            raise

def get_storage_bucket():
    """Get Firebase Storage bucket (ensure Firebase initialized)"""
    initialize_firebase()
    return storage.bucket()
