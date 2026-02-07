try:
    from ..main.firebase_config import initialize_firebase
   
except Exception as e:
    print(f"⚠️ Warning: Could not initialize Firebase: {e}")