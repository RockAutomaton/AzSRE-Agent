import json
import requests
import sys
import time
from pathlib import Path


# Configuration
API_URL = "http://localhost:8000/webhook/azure"


def trigger_simulation():
    # Allow overriding the mock file via command line arg
    filename = "mock_payload.json"
    if len(sys.argv) > 1:
        filename = sys.argv[1]

    MOCK_FILE = Path(__file__).parent.parent / "tests" / filename
    
    print(f"🚀 Loading mock alert from: {MOCK_FILE}")
    
    if not MOCK_FILE.exists():
        print(f"❌ Error: File not found at {MOCK_FILE}")
        sys.exit(1)

    try:
        with open(MOCK_FILE, "r") as f:
            payload = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Error: Failed to parse JSON from {MOCK_FILE}")
        print(f"   {type(e).__name__}: {str(e)}")
        sys.exit(1)
    except OSError as e:
        print(f"❌ Error: Failed to read file {MOCK_FILE}")
        print(f"   {type(e).__name__}: {str(e)}")
        sys.exit(1)

    print(f"📡 Sending Webhook to {API_URL}...")
    alert_rule = payload.get('data', {}).get('essentials', {}).get('alertRule')
    if alert_rule is None:
        print("⚠️  Warning: alertRule not found in payload structure")
        alert_rule = "Unknown"
    print(f"   Alert Rule: {alert_rule}")
    
    try:
        start_time = time.time()
        response = requests.post(API_URL, json=payload)
        duration = time.time() - start_time

        if response.status_code == 200:
            print(f"✅ Success! (Took {duration:.2f}s)")
            result = response.json()
            
            print("\n--- 🤖 AGENT REPORT ---")
            print(f"Classification: {result.get('classification')}")
            print(f"Report:\n{result.get('report')}")
            print("-----------------------")
        else:
            print(f"❌ Failed with Status {response.status_code}")
            print(response.text)

    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to localhost:8000. Is Docker running?")


if __name__ == "__main__":
    trigger_simulation()

