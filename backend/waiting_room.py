import time
import uuid
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException
from redis import Redis
from pydantic import BaseModel


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all browsers to connect
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# PASTE YOUR REDIS CLOUD DETAILS HERE
# ---------------------------------------------------------
REDIS_HOST = "redis-15340.c12.us-east-1-4.ec2.cloud.redislabs.com"  # e.g., redis-18000.c1...
REDIS_PORT = 15340                   # e.g., 18000
REDIS_PASSWORD = "UJRWKGmxCs5TR6e1WjJkR31yQr4t3Lzq"
# ---------------------------------------------------------

# Connect to the remote Redis Cloud
try:
    redis_client = Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD,
        decode_responses=True # This makes sure we get Strings, not Bytes
    )
    redis_client.ping() # Test connection
    print("✅ Connected to Redis Cloud successfully!")
except Exception as e:
    print(f"❌ Failed to connect to Redis: {e}")

# CONFIGURATION
CONFIG={"max_capacity":5}      # Only 50 people allowed in the "club"
WAITING_ROOM_KEY = "queue"
ACTIVE_USERS_KEY = "active"

@app.post("/join")
def join_waiting_room():
    """User hits the site. We give them a ticket number."""
    user_id = str(uuid.uuid4())
    arrival_time = time.time()
    
    # Add to the Waiting Line (Sorted by time)
    redis_client.zadd(WAITING_ROOM_KEY, {user_id: arrival_time})
    
    return {"user_id": user_id, "message": "You are in line."}

@app.get("/status/{user_id}")
def check_status(user_id: str):
    """User asks: 'Can I enter yet?'"""
    
    # 1. Check if they are already inside
    if redis_client.sismember(ACTIVE_USERS_KEY, user_id):
        return {"status": "admitted", "url": "http://cool-website.com/buy"}

    # 2. Check their position in the line
    rank = redis_client.zrank(WAITING_ROOM_KEY, user_id)
    
    if rank is None:
        raise HTTPException(status_code=404, detail="User not found. Please /join first.")
    
    # 3. Check if the Club is full
    active_count = redis_client.scard(ACTIVE_USERS_KEY)
    
    # LOGIC: If there is space AND this user is next in line
    if active_count < CONFIG["max_capacity"] and rank == 0:
        # Move them from Queue -> Active
        redis_client.zrem(WAITING_ROOM_KEY, user_id)
        redis_client.sadd(ACTIVE_USERS_KEY, user_id)
        return {"status": "admitted", "url": "http://cool-website.com/buy"}
    
    return {"status": "waiting", "position": rank + 1}

@app.post("/leave/{user_id}")
def leave(user_id: str):
    """User leaves the site, freeing up a spot."""
    redis_client.srem(ACTIVE_USERS_KEY, user_id)
    return {"message": "You left the club."}

@app.post("/reset")
def reset_club():
    """Admin only: Wipes the entire database to start fresh."""
    redis_client.flushdb()
    return {"message": "Database cleared. The club is empty."}

class ConfigUpdate(BaseModel):
    new_capacity:int

@app.get('/admin/stats')
def get_global_stats():
    queue_count=redis_client.zcard(WAITING_ROOM_KEY)
    active_count=redis_client.scard(ACTIVE_USERS_KEY)

    return{
        "waiting_in_queue": queue_count,
        "currently_active": active_count,
        "current_capacity_limit": CONFIG["max_capacity"]
    }

@app.post("/admin/config")
def update_config(data:ConfigUpdate):
    old_cap=CONFIG["max_capacity"]
    CONFIG["max_capacity"]=data.new_capacity
    print(f" Admin changed capacity from {old_cap} to {data.new_capacity}")

    return{
        "message": f'Capacity updated to {data.new_capacity}'
    }