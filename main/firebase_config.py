import json
import os
import firebase_admin
from firebase_admin import credentials, storage

def initialize_firebase():
    if not firebase_admin._apps:
        cred = credentials.Certificate(
            json.loads(os.environ["FIREBASE_SERVICE_ACCOUNT"])
        )
        firebase_admin.initialize_app(cred, {
            "storageBucket": "daroui.appspot.com"
        })
        print("✅ Firebase initialized")

def get_storage_bucket():
    # تأكد أن Firebase تم تهيئته قبل أي استخدام
    initialize_firebase()
    return storage.bucket()
