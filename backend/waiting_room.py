import time
import asyncio
import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import redis
from dotenv import load_dotenv

# 1. Load Environment Variables
load_dotenv()

app = FastAPI()

# 2. CORS Setup (Allow your Vercel frontend to talk to this)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://traffi-control.vercel.app/demo.html"],  # In production, replace * with your Vercel URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Connect to Redis
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST"),
    port=os.getenv("REDIS_PORT"),
    password=os.getenv("REDIS_PASSWORD"),
    decode_responses=True
)

# --- CONFIGURATION ---
# We store these in Redis so we can update them on the fly
DEFAULT_CAPACITY = 5
INACTIVE_TIMEOUT = 20 # Seconds (Short timeout for demo purposes)

# --- 4. THE MANAGER LOGIC (Integrated) ---
async def run_queue_manager():
    """
    This background task acts as the 'Bouncer'.
    It runs inside the same server, checking every 2 seconds.
    """
    print("🚀 Queue Manager started in background...")
    while True:
        try:
            # A. Get current limits
            cap = redis_client.get("max_capacity")
            MAX_CAPACITY = int(cap) if cap else DEFAULT_CAPACITY

            # B. Clean up "Dead" users (Zombies)
            # We look for people who haven't pinged in 20 seconds
            now = time.time()
            cutoff = now - INACTIVE_TIMEOUT
            
            # 'active_users' is a Sorted Set where score = last_seen_timestamp
            # Remove anyone with score < cutoff
            removed_count = redis_client.zremrangebyscore("active_users", 0, cutoff)
            if removed_count > 0:
                print(f"💀 Removed {removed_count} inactive users.")

            # C. Move people from Queue -> Active
            # Check how many seats are free
            active_count = redis_client.zcard("active_users")
            slots_free = MAX_CAPACITY - active_count

            if slots_free > 0:
                # Pop 'slots_free' amount of users from the queue (FIFO)
                # zpopmin removes the user with the lowest score (earliest arrival)
                admitted_users = redis_client.zpopmin("queue", slots_free)
                
                for user_data in admitted_users:
                    user_id = user_data[0]
                    # Add them to active_users set with current timestamp
                    redis_client.zadd("active_users", {user_id: time.time()})
                    print(f"🎉 Admitted user: {user_id}")

        except Exception as e:
            print(f"❌ Manager Error: {e}")
        
        # Sleep for 2 seconds before checking again
        await asyncio.sleep(2)

# --- 5. STARTUP EVENT ---
@app.on_event("startup")
async def startup_event():
    # This tells FastAPI to start the manager loop when the server starts
    asyncio.create_task(run_queue_manager())


# --- 6. API ENDPOINTS ---

class ConfigUpdate(BaseModel):
    max_capacity: int

@app.post("/join")
def join():
    import uuid
    user_id = str(uuid.uuid4())
    # Add to queue with score = current time
    redis_client.zadd("queue", {user_id: time.time()})
    return {"user_id": user_id, "message": "Joined queue"}

@app.get("/status/{user_id}")
def get_status(user_id: str):
    # 1. Check if user is already Active
    # Also UPDATE their "last_seen" time (Heartbeat)
    score = redis_client.zscore("active_users", user_id)
    if score:
        # User is active! Update their timestamp so they don't get kicked
        redis_client.zadd("active_users", {user_id: time.time()})
        return {"status": "admitted", "position": 0}

    # 2. Check if user is in Queue
    rank = redis_client.zrank("queue", user_id)
    if rank is not None:
        # Rank is 0-indexed, so add 1 for human readability
        return {"status": "queued", "position": rank + 1}

    # 3. User not found (Reset or Expired)
    # Return 404 so the frontend knows to get a new ticket
    raise HTTPException(status_code=404, detail="User not found")

@app.get("/admin/stats")
def stats():
    active = redis_client.zcard("active_users")
    queued = redis_client.zcard("queue")
    cap = redis_client.get("max_capacity")
    return {
        "active_users": active,
        "queued_users": queued,
        "max_capacity": int(cap) if cap else DEFAULT_CAPACITY
    }

@app.post("/admin/config")
def update_config(config: ConfigUpdate):
    redis_client.set("max_capacity", config.max_capacity)
    return {"message": "Updated capacity"}

@app.post("/admin/reset")
def reset_system():
    redis_client.delete("queue")
    redis_client.delete("active_users")
    return {"message": "System reset"}