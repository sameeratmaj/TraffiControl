import requests
import time
import random

BASE_URL = "http://127.0.0.1:8000"

print("--- MANAGER STARTED: Kicking people out every 3 seconds ---")

while True:
    try:
        # 1. Start the loop
        time.sleep(3) 
        
        # NOTE: We are "cheating" here by accessing Redis directly via API 
        # normally we would need an endpoint to "get all active users", 
        # but for now, we will just simulate spots opening up by clearing the active list slowly.
        
        # Actually, the easiest way to make space is to just tell the server "Someone left"
        # Since we don't know the IDs of the strangers in the club, let's use a trick.
        # We will use the Redis Client directly to find a victim.
        
        from redis import Redis
        # PASTE YOUR REDIS DETAILS HERE IF USING CLOUD, OR DEFAULT FOR LOCAL
        #r = Redis(host='redis-15340.c12.us-east-1-4.ec2.cloud.redislabs.com', port=15340, decode_responses=True)
        # If using Cloud, uncomment and fill this:
        r = Redis(host='redis-15340.c12.us-east-1-4.ec2.cloud.redislabs.com', port=15340, password='UJRWKGmxCs5TR6e1WjJkR31yQr4t3Lzq', decode_responses=True)
        
        active_users = r.smembers("active") # Get list of people inside
        
        if active_users:
            victim = list(active_users)[0] # Pick the first person
            
            # Kick them out using our API
            requests.post(f"{BASE_URL}/leave/{victim}")
            print(f"👋 Manager kicked out user: {victim[:5]}... -> Spot Opened!")
        else:
            print("Club is empty. Waiting for people...")
            
    except Exception as e:
        print(f"Error: {e}")
        # If redis isn't installed in this script, install it: pip install redis