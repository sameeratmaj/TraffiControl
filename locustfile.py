from locust import HttpUser, task, between
import random

class QueueUser(HttpUser):
    wait_time = between(2,5) # Poll every 1-2 seconds
    
    def on_start(self):
        self.user_id = None
        self.active_loops = 0 # Count how long we've been inside

    @task
    def flow(self):
        # 1. JOIN
        if not self.user_id:
            with self.client.post("/join", catch_response=True) as response:
                if response.status_code == 200:
                    self.user_id = response.json().get("user_id")

        # 2. POLL STATUS
        else:
            with self.client.get(f"/status/{self.user_id}", catch_response=True) as response:
                if response.status_code == 200:
                    data = response.json()
                    status = data.get("status")
                    
                    if status == "active":
                        self.active_loops += 1
                        
                        # 🎲 SIMULATION: Buy ticket after ~5-10 seconds (5 loops)
                        # This clears the spot for the next person!
                        if self.active_loops > random.randint(3, 8):
                            self.buy_ticket()

                    elif status == "expired":
                        self.user_id = None # Rejoin as new person
                        self.active_loops = 0

                elif response.status_code == 404:
                    self.user_id = None
                    self.active_loops = 0

    def buy_ticket(self):
        """Simulates clicking the Buy button"""
        self.client.post(f"/checkout/{self.user_id}")
        # print(f"💰 User {self.user_id} bought a ticket and left!")
        self.user_id = None # Leave the system
        self.active_loops = 0