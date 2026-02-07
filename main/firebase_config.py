import json, os
import firebase_admin
from firebase_admin import credentials, storage

def get_storage_bucket():
    if not firebase_admin._apps:
        cred = credentials.Certificate(
            json.loads(os.environ["FIREBASE_SERVICE_ACCOUNT"])
        )
        firebase_admin.initialize_app(cred, {
            "storageBucket": "daroui.appspot.com"
        })
    return storage.bucket()
