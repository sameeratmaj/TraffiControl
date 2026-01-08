(async function() {
    // ⚠️ UPDATE THIS URL if needed
    const API_URL = "https://trafficontrol.onrender.com"; 

    let userId = localStorage.getItem("gatekeeper_id");

    // --- 1. THE DESIGN (The Curtain) ---
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

    // --- 2. JOIN LOGIC (Helper Function) ---
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

    // Initialize if no ID exists
    if (!userId) {
        userId = await joinQueue();
    }

    // --- 3. CHECK STATUS & AUTO-HEAL ---
    const checkStatus = async () => {
        if (!userId) return; // Stop if we failed to join

        try {
            const r = await fetch(`${API_URL}/status/${userId}`);
            
            // 🚨 FIX: If Server says "404 Not Found" (Reset happened), Re-join immediately!
            if (r.status === 404) {
                console.log("Ticket invalid (System Reset?). Getting new ticket...");
                localStorage.removeItem("gatekeeper_id");
                userId = await joinQueue(); // Get new ID
                return; // Restart loop next tick
            }

            const d = await r.json();

            // 🚨 FIX: If position is undefined, don't show it.
            if (d.position === undefined && d.status !== "admitted") {
                 // Fallback: If status is weird, just assume admitted or retry
                 return; 
            }

            if (d.status !== "admitted") {
                // INJECT OVERLAY
                if (!document.getElementById("gk-overlay")) {
                    document.body.insertAdjacentHTML('beforeend', overlayHTML);
                    document.body.style.overflow = "hidden";
                }
                
                // Update position
                document.getElementById("gk-position").innerText = d.position;
                
                // Check again in 2 seconds
                setTimeout(checkStatus, 2000);
            } else {
                // REMOVE OVERLAY
                const overlay = document.getElementById("gk-overlay");
                if (overlay) {
                    overlay.remove();
                    document.body.style.overflow = "auto";
                }
            }
        } catch (e) {
            console.error("Connection lost", e);
        }
    };

    // Start the loop
    setInterval(checkStatus, 3000); // More reliable than recursive setTimeout for this case
    checkStatus(); // Run once immediately
})();