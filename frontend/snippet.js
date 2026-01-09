(async function() {
    // ⚠️ CONFIGURATION
    const API_URL = "https://trafficontrol.onrender.com"; 


    let userId = localStorage.getItem("gatekeeper_id");
    let isReconnecting = false;

    // --- 1. HTML TEMPLATES ---
    
    // The Countdown Timer (Shown when Active)
    const timerHTML = `
        <div id="gk-timer" style="position:fixed; bottom:20px; right:20px; background:#e74c3c; color:white; padding:15px; border-radius:50px; font-family:sans-serif; font-weight:bold; font-size:20px; box-shadow:0 4px 10px rgba(0,0,0,0.3); z-index:10000; display:none;">
            ⏱️ <span id="gk-countdown">--</span>s
        </div>
    `;

    // The Waiting Room Curtain (Shown when Queued)
    const overlayHTML = `
        <div id="gk-overlay" style="position:fixed; top:0; left:0; width:100%; height:100%; background:white; z-index:9999; display:flex; flex-direction:column; align-items:center; justify-content:center; font-family:sans-serif;">
            <h1 style="color:#e74c3c; font-size: 2rem;">🚦 Traffic Control</h1>
            <p style="color:#333; margin-top: 10px;">We are experiencing high demand.</p>
            <div style="background:#f0f0f0; padding: 20px; border-radius: 10px; margin: 20px 0; text-align: center;">
                <div style="font-size:14px; color:#666;">Your Position</div>
                <div style="font-size:40px; font-weight:bold; color:#2c3e50;" id="gk-position">--</div>
            </div>
            <p style="font-size: 12px; color: #999;">Please do not refresh the page.</p>
        </div>
    `;

    // --- 2. JOIN LOGIC ---
    async function joinQueue() {
        try {
            const r = await fetch(`${API_URL}/join`, { method: "POST" });
            const d = await r.json();
            localStorage.setItem("gatekeeper_id", d.user_id);
            return d.user_id;
        } catch(e) {
            console.error("Server Down?", e);
            return null;
        }
    }

    if (!userId) {
        userId = await joinQueue();
    }

    // --- 3. CHECK STATUS LOOP ---
    const checkStatus = async () => {
        if (!userId) return; 

        try {
            const r = await fetch(`${API_URL}/status/${userId}`);

            // A. HANDLE RESET / 404 (Auto-Rejoin)
            if (r.status === 404) {
                if(isReconnecting) return;
                console.log("Ticket invalid. Attempting auto-rejoin...");
                isReconnecting = true;
                try {
                    localStorage.removeItem("gatekeeper_id");
                    userId = await joinQueue();
                } finally {
                    isReconnecting = false;
                }
                return;
            }

            // B. HANDLE NORMAL RESPONSE
            if (r.status === 200) {
                const d = await r.json();

                // 💀 Case 1: EXPIRED (Time's up!)
                if (d.status === "expired") {
                    alert("Session Expired! You took too long.");
                    localStorage.removeItem("gatekeeper_id");
                    window.location.replace("timeout.html")
                    return;
                }

                // 🟢 Case 2: ACTIVE (Show Website + Timer)
                if (d.status === "active") {
                    // Remove Curtain if it exists
                    const overlay = document.getElementById("gk-overlay");
                    if (overlay) { overlay.remove(); document.body.style.overflow = "auto"; }

                    // Inject Timer if missing
                    if(!document.getElementById("gk-timer")) {
                        document.body.insertAdjacentHTML('beforeend', timerHTML);
                    }
                    
                    // Show & Update Timer
                    const timerBox = document.getElementById("gk-timer");
                    timerBox.style.display = "block";
                    // Only update if time_remaining is sent
                    if(d.time_remaining !== undefined) {
                        const currentVal = parseInt(document.getElementById("gk-countdown").innerText);
                        // Only update if the new number is SMALLER or if current is --
                        if (isNaN(currentVal) || d.time_remaining < currentVal) {
                             document.getElementById("gk-countdown").innerText = d.time_remaining;
                        }
                    }
                }

                // 🔴 Case 3: QUEUED (Show Curtain)
                if (d.status === "queued") {
                    // Hide Timer
                    if(document.getElementById("gk-timer")) {
                        document.getElementById("gk-timer").style.display = "none";
                    }

                    // Inject Curtain if missing
                    if (!document.getElementById("gk-overlay")) {
                        document.body.insertAdjacentHTML('beforeend', overlayHTML);
                        document.body.style.overflow = "hidden";
                    }
                    // Update Position Number
                    document.getElementById("gk-position").innerText = d.position;
                }
            }
        } catch (e) {
            console.error("Connection lost", e);
        }
    };

    // --- 4. BUY BUTTON LOGIC ---
    // This attaches to the global window object so your HTML button can call it
    window.buyTicket = async function() {
        if(!userId) return;
        try {
            await fetch(`${API_URL}/checkout/${userId}`, { method: "POST" });
            localStorage.removeItem("gatekeeper_id");
            window.location.replace("success.html");
        } catch(e) {
            alert("Checkout failed. Check internet.");
        }
    };

    // --- 5. START ---
    setInterval(checkStatus, 1000); // Check every 1s for accurate timer
    checkStatus(); 

})();