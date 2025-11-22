import asyncio
import aiohttp
import os
import sys
import time
from collections import defaultdict
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Default Configuration (can be overridden via environment variables)
DEFAULT_URL = os.getenv("TRAFFIC_GEN_URL", "http://localhost:8000")
DEFAULT_REQUESTS = int(os.getenv("TRAFFIC_GEN_REQUESTS", "1000"))
CONCURRENCY = int(os.getenv("TRAFFIC_GEN_CONCURRENCY", "50"))


async def send_request(session, url, stats):
    start = time.time()
    try:
        async with session.get(url) as response:
            # Read body to ensure request completes
            await response.read()
            stats["total"] += 1
            stats[response.status] += 1
    except Exception as e:
        stats["errors"] += 1
        # Optional: print error if verbose
        # print(f"Request failed: {str(e)}")
    finally:
        stats["latency"].append(time.time() - start)


async def main(target_url, count, concurrency):
    print(f"🚀 Starting Traffic Flood: {count} requests => {target_url}")
    print(f"   Concurrency: {concurrency}")
    print("   Sending", end="", flush=True)
    
    stats = defaultdict(int)
    stats["latency"] = []
    
    start_time = time.time()
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        for _ in range(count):
            tasks.append(send_request(session, target_url, stats))
            
            # Simple concurrency control (batching)
            if len(tasks) >= concurrency:
                await asyncio.gather(*tasks)
                tasks = []
                print(".", end="", flush=True)
        
        # Finish remaining tasks
        if tasks:
            await asyncio.gather(*tasks)

    duration = time.time() - start_time
    rps = count / duration if duration > 0 else 0
    
    print(f"\n\n✅ Completed in {duration:.2f}s")
    print(f"📊 Stats:")
    print(f"   Requests/Sec: {rps:.2f}")
    print(f"   Status 200:   {stats[200]}")
    print(f"   Status 500:   {stats[500]}")
    print(f"   Errors:       {stats['errors']}")
    
    if stats["latency"]:
        avg_lat = sum(stats["latency"]) / len(stats["latency"])
        max_lat = max(stats["latency"])
        print(f"   Avg Latency:  {avg_lat*1000:.2f}ms")
        print(f"   Max Latency:  {max_lat*1000:.2f}ms")


if __name__ == "__main__":
    # Usage: python scripts/chaos/traffic_gen.py [URL] [COUNT] [CONCURRENCY]
    # Environment variables (via .env file):
    #   TRAFFIC_GEN_URL - Default target URL
    #   TRAFFIC_GEN_REQUESTS - Default request count
    #   TRAFFIC_GEN_CONCURRENCY - Default concurrency level
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    count = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_REQUESTS
    concurrency = int(sys.argv[3]) if len(sys.argv) > 3 else CONCURRENCY
    
    try:
        asyncio.run(main(url, count, concurrency))
    except KeyboardInterrupt:
        print("\n🛑 Stopped.")

