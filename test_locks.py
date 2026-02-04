import requests
import time
import sys

BASE_URL = "http://127.0.0.1:8000"
TABLE_NUMBER = "1"

def log(msg):
    print(msg)
    sys.stdout.flush()

def create_session(user_agent, ip_header=None):
    headers = {"User-Agent": user_agent}
    if ip_header:
        headers["X-Forwarded-For"] = ip_header
        
    try:
        log(f"Requesting session for UA: {user_agent[:20]}...")
        response = requests.post(
            f"{BASE_URL}/public/table-sessions/create/",
            json={"table_number": TABLE_NUMBER},
            headers=headers,
            timeout=5
        )
        return response
    except Exception as e:
        log(f"Request exception: {e}")
        return None

def test_locking():
    log(f"--- Testing Table Locking for Table {TABLE_NUMBER} ---")
    
    # 1. Client A (Chrome)
    log("\n1. Client A (Chrome) connects...")
    resp_a = create_session("Mozilla/5.0 (Chrome/120)")
    
    if resp_a and resp_a.status_code in [200, 201]:
        log(f"✅ Client A Connected: {resp_a.status_code}")
        data = resp_a.json()
        log(f"   Token: {data['session']['token'][:10]}...")
        log(f"   Resumed: {data.get('resumed', False)}")
    else:
        log(f"❌ Client A Failed: {resp_a.status_code if resp_a else 'No Response'}")
        if resp_a: log(resp_a.text)
        return

    # 2. Client B (Firefox) - Should be BLOCKED
    log("\n2. Client B (Firefox) connects (Different UA)...")
    resp_b = create_session("Mozilla/5.0 (Firefox/115)")
    
    if resp_b and resp_b.status_code == 409:
        log(f"✅ Client B Blocked: {resp_b.status_code}")
        log(f"   Error: {resp_b.json()['error']}")
    elif resp_b and resp_b.status_code in [200, 201]:
        log(f"❌ Client B Allowed (SHOULD BE BLOCKED): {resp_b.status_code}")
        log(f"   Data: {resp_b.json()}")
    else:
        log(f"❓ Client B Expected 409, got: {resp_b.status_code if resp_b else 'No Response'}")

    # 3. Client A again (Chrome) - Should RESUME
    log("\n3. Client A (Chrome) reconnects...")
    resp_a2 = create_session("Mozilla/5.0 (Chrome/120)")
    
    if resp_a2 and resp_a2.status_code in [200, 201]:
        log(f"✅ Client A Resumed: {resp_a2.status_code}")
        log(f"   Resumed: {resp_a2.json().get('resumed', False)}")
    else:
        log(f"❌ Client A Failed to resume: {resp_a2.status_code if resp_a2 else 'No Response'}")

if __name__ == "__main__":
    try:
        import requests
        test_locking()
    except ImportError:
        print("Error: 'requests' library not found. Please install it.")
