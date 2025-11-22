import json
import requests
import sys
import time
from pathlib import Path


# Configuration
API_URL = "http://localhost:8000/webhook/azure"
MOCK_FILE = Path(__file__).parent.parent / "tests" / "mock_payload.json"


def trigger_simulation():
    print(f"🚀 Loading mock alert from: {MOCK_FILE}")
    
    if not MOCK_FILE.exists():
        print(f"❌ Error: File not found at {MOCK_FILE}")
        sys.exit(1)

    with open(MOCK_FILE, "r") as f:
        payload = json.load(f)

    print(f"📡 Sending Webhook to {API_URL}...")
    print(f"   Alert Rule: {payload['data']['essentials']['alertRule']}")
    
    try:
        start_time = time.time()
        response = requests.post(API_URL, json=payload)
        duration = time.time() - start_time

        if response.status_code == 200:
            print(f"✅ Success! (Took {duration:.2f}s)")
            result = response.json()
            
            print("\n--- 🤖 AGENT REPORT ---")
            print(f"Classification: {result['classification']}")
            print(f"Report:\n{result['report']}")
            print("-----------------------")
        else:
            print(f"❌ Failed with Status {response.status_code}")
            print(response.text)

    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to localhost:8000. Is Docker running?")


if __name__ == "__main__":
    trigger_simulation()

