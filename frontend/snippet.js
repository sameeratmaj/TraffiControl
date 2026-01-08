(async function() {
    // ⚠️ IMPORTANT: Replace this with your deployed Render URL
    const API_URL = "https://your-api-url.onrender.com"; 

    let userId = localStorage.getItem("gatekeeper_id");

    // --- 1. THE DESIGN (This is the "Curtain") ---
    // We store the HTML inside a JavaScript string so we can inject it later.
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
    if (!userId) {
        try {
            const r = await fetch(`${API_URL}/join`, { method: "POST" });
            const d = await r.json();
            userId = d.user_id;
            localStorage.setItem("gatekeeper_id", userId);
        } catch(e) { 
            console.log("Server down, letting user in."); 
            return; 
        } 
    }

    // --- 3. CHECK STATUS & INJECT OVERLAY ---
    const checkStatus = async () => {
        try {
            const r = await fetch(`${API_URL}/status/${userId}`);
            const d = await r.json();

            if (d.status !== "admitted") {
                // [THE DOM INJECTION PART]
                // If the curtain doesn't exist yet, ADD IT to the page body
                if (!document.getElementById("gk-overlay")) {
                    document.body.insertAdjacentHTML('beforeend', overlayHTML);
                    document.body.style.overflow = "hidden"; // Freeze scrolling
                }
                
                // Update the position number
                document.getElementById("gk-position").innerText = d.position;
                
                // Check again in 3 seconds
                setTimeout(checkStatus, 3000);
            } else {
                // [THE REMOVAL PART]
                // User is admitted! Remove the curtain.
                const overlay = document.getElementById("gk-overlay");
                if (overlay) {
                    overlay.remove();
                    document.body.style.overflow = "auto"; // Unfreeze scrolling
                }
            }
        } catch (e) {
            console.error("Connection lost", e);
        }
    };

    // Start the loop
    checkStatus();
})();