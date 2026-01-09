# 🚦 TraffiControl: High-Concurrency Virtual Waiting Room

![Python](https://img.shields.io/badge/Python-FastAPI-blue?style=for-the-badge&logo=python)
![Redis](https://img.shields.io/badge/Redis-In--Memory_DB-red?style=for-the-badge&logo=redis)
![Locust](https://img.shields.io/badge/Locust-Load_Testing-green?style=for-the-badge&logo=locust)

**TraffiControl** is a system design project that protects websites from crashing during traffic spikes (e.g., Flash Sales, Ticket Releases). It implements a **Fairness-First Queue System** that throttles traffic, manages user sessions, and prevents abuse using advanced Redis patterns.

---

## 🏗️ System Architecture

The system is designed to handle high concurrency on low-resource hardware (0.1 vCPU) by offloading state management to Redis.

### Key Components
1.  **The Bouncer (Rate Limiter):** - Intercepts every user request.
    - Checks `Active User Capacity` vs `Max Limit`.
    - **Instant Access Logic:** If capacity < limit, users skip the queue entirely for 0-latency access.
    
2.  **The Ghost Killer (Dead Connection Cleanup):**
    - Uses a **Heartbeat Mechanism** (Frontend pings every 1s).
    - Background worker (Python) scans Redis for "zombie" users who closed the tab but didn't logout.
    - **Outcome:** Frees up spots in ~15 seconds, maximizing throughput.

3.  **The "Two-Clock" Session Manager:**
    - Solves the "Frozen Timer" concurrency bug.
    - **Clock 1 (Monotonic):** Tracks exact Session Start Time (Immutable).
    - **Clock 2 (Heartbeat):** Tracks Last Seen Activity (Mutable).
    - Ensures users are kicked out precisely at the **40s Session Limit**, preventing squatting.

---

## 🚀 Engineering Challenges & Solutions

### 1. The "100-Tab" Attack (Concurrency Control)
* **Problem:** A single user opening 100 tabs could flood the queue, taking spots from others.
* **Solution:** Implemented **IP-Based Atomic Locking** in Redis.
* **Result:** Multiple tabs from the same device share a *single* queue position and session timer. They act as "mirrors" of the same user ID.

### 2. The Free Tier Bottleneck (Optimization)
* **Problem:** The hosting environment (Render Free Tier) is limited to 0.1 vCPU and 50 Redis connections.
* **Initial Fail:** Load testing crashed the server at 20 concurrent users due to connection leaks.
* **Optimization:** Implemented **Global Redis Connection Pooling** to reuse 20 permanent connections for thousands of requests.
* **Result:** Throughput increased by **500%** (Stable at 35-40 concurrent active users on 0.1 vCPU).

---

## 📊 Load Testing Results (Locust)

I performed stress testing using **Locust** to determine the breaking point of the architecture.

| Metric | Result (Free Tier) | Notes |
| :--- | :--- | :--- |
| **Max Concurrent Users** | ~40 | Stable response < 500ms |
| **Breaking Point** | ~80 Users | Response time spikes > 2000ms |
| **Max Throughput** | 25 RPS | CPU Bottleneck (0.1 vCPU limit) |

**Stress Test Chart:**
> ![Locust Stress Test Results]
> (assets/locust_chart-100-users.png)
> *The yellow line shows latency spiking when CPU saturation is reached at ~80 users.*

---

## 🛠️ Tech Stack

* **Backend:** Python (FastAPI) - Chosen for high-performance async capabilities.
* **Database:** Redis - Used for sorted sets (Queue), atomic counters, and key-value expiry.
* **Frontend:** Vanilla JS - Lightweight snippet (<2KB) that can be injected into any website.
* **Testing:** Locust - Distributed load testing.

---

## 💻 Installation & Setup

### Prerequisites
* Python 3.9+
* Redis Server (Local or Cloud)

### 1. Clone the Repo
```bash
git clone [https://github.com/yourusername/trafficontrol.git](https://github.com/yourusername/trafficontrol.git)
cd trafficontrol