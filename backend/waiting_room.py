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

# Configuration
SESSION_LIMIT = 40

app = FastAPI()

# 2. CORS Setup (Allow your Vercel frontend to talk to this)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace * with your Vercel URL
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
    max_connections=20
)

# --- CONFIGURATION ---
# We store these in Redis so we can update them on the fly
DEFAULT_CAPACITY = 5
INACTIVE_TIMEOUT =5 # Seconds (Short timeout for demo purposes)

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
    
    # 1. GET CURRENT CAPACITY LIMIT
    # We fetch the limit you set in the dashboard (default to 5 if missing)
    max_cap = redis_client.get("max_capacity")
    limit = int(max_cap) if max_cap else 5

    # 2. CHECK CURRENT CROWD SIZE
    active_count = redis_client.zcard("active_users")

    # 3. THE INSTANT DECISION
    if active_count < limit:
        # 🚀 VIP FAST-TRACK (Room is empty -> Enter immediately)
        now = time.time()
        
        # A. Add to Active (For Ghost Killer)
        redis_client.zadd("active_users", {user_id: now})
        
        # B. Start Session Timer (For 40s Limit) - CRITICAL!
        redis_client.setex(f"session_start:{user_id}", 60, now)
        
        return {"user_id": user_id, "status": "active", "message": "Direct entry"}
        
    else:
        # 🐢 WAITING ROOM (Room is full -> Get in line)
        redis_client.zadd("queue", {user_id: time.time()})
        return {"user_id": user_id, "status": "queued", "message": "Joined queue"}

@app.get("/status/{user_id}")
def get_status(user_id: str):

    tombstone=redis_client.get(f"status:{user_id}")
    if tombstone == "expired":
        return {"status":"expired"}
    if tombstone == "completed":
        return{"status": "completed"}
    
    # 1. Check if user is already Active
    # Also UPDATE their "last_seen" time (Heartbeat)
    score = redis_client.zscore("active_users", user_id)
    if score:
        # User is active! Update their timestamp so they don't get kicked
        redis_client.zadd("active_users", {user_id: time.time()})
        #return {"status": "admitted", "position": 0}
        start_key=f"session_start:{user_id}"
        start_time=redis_client.get(start_key)
        if not start_time:
            start_time=time.time()
            redis_client.setex(start_key,60,start_time)
        else:
            start_time=float(start_time)
            time_spent = time.time()-start_time

            if time_spent >SESSION_LIMIT:
                redis_client.zrem("active_users",user_id)
                redis_client.delete(start_key)
                redis_client.setex(f"status:{user_id}",30,"expired")
                return {"status" : "expired"}
        
        return{
            "status":"active",
            "time_remaining":int(SESSION_LIMIT-time_spent)
        }

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

@app.post("/checkout/{user_id}")
def checkout_user(user_id:str):
    redis_client.zrem('active_users',user_id)
    redis_client.setex(f"status:{user_id}",30,"completed")
    return {"status":"completed"}