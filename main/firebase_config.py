import json
import os
import firebase_admin
from firebase_admin import credentials, storage

def initialize_firebase():
    if not firebase_admin._apps:
        cred = credentials.Certificate(
            json.loads(os.environ["FIREBASE_SERVICE_ACCOUNT"])
        )
        bucket_name = os.environ.get("FIREBASE_BUCKET_NAME", "daroui.appspot.com")
        firebase_admin.initialize_app(cred, {
            "storageBucket": bucket_name
        })
        print(f"✅ Firebase initialized with bucket: {bucket_name}")

def get_storage_bucket():
    initialize_firebase()
    return storage.bucket()
