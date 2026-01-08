import requests
import time
import threading
import random

BASE_URL = "http://127.0.0.1:8000"

def bot_lifecycle(bot_id):
    try:
        # 1. Join
        print(f"🤖 Bot {bot_id}: Joining queue...")
        resp = requests.post(f"{BASE_URL}/join").json()
        user_id = resp['user_id']
        
        # 2. Poll until admitted
        while True:
            status_resp = requests.get(f"{BASE_URL}/status/{user_id}").json()
            
            if status_resp['status'] == "admitted":
                print(f"✅ Bot {bot_id}: GOT IN! Spending 5 seconds inside...")
                time.sleep(5) # Pretend to buy ticket
                
                # 3. Leave
                requests.post(f"{BASE_URL}/leave/{user_id}")
                print(f"👋 Bot {bot_id}: Bought ticket and LEFT.")
                break
            
            else:
                # Still waiting
                pos = status_resp.get('position', '?')
                # Don't spam print, just wait
                time.sleep(2)
                
    except Exception as e:
        print(f"Bot {bot_id} died: {e}")

print("--- STARTING LIVE TRAFFIC SIMULATION ---")
# Launch 10 bots
threads = []
for i in range(1, 11):
    t = threading.Thread(target=bot_lifecycle, args=(i,))
    threads.append(t)
    t.start()
    time.sleep(0.5) # Stagger them so they don't all join at the exact same millisecond

# Keep main script alive
for t in threads:
    t.join()