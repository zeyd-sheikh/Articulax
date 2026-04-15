const micStatus = document.getElementById("mic_status");
const startButton = document.getElementById("start_session_btn");

async function requestMicPermission() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        if (micStatus) {
            micStatus.textContent = "Microphone is not supported here.";
        }
        return false;
    }

    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

        stream.getTracks().forEach(track => track.stop());

        if (micStatus) {
            micStatus.textContent = "Microphone ready.";
        }

        return true;
    } 
    
    catch (err) {
        if (micStatus) {
            if (err.name === "NotAllowedError") {
                micStatus.textContent = "Microphone permission was denied.";
            } 
            else if (err.name === "NotFoundError") {
                micStatus.textContent = "No microphone was found.";
            } 
            else {
                micStatus.textContent = "Could not access the microphone.";
            }
        }

        console.error("Microphone error:", err);
        return false;
    }
}

window.addEventListener("DOMContentLoaded", async function () {
    const micReady = await requestMicPermission();

    if (startButton) {
        startButton.disabled = !micReady;
    }
});
