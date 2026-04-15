const micStatus = document.getElementById("mic_status");
const enableMicButton = document.getElementById("enable_mic_btn");
const startButton = document.getElementById("start_session_btn");
const cancelButton = document.getElementById("cancel_session_btn");
const backButton = document.getElementById("back_to_dashboard_btn");
const sessionStatusBox = document.getElementById("session_status_box");
const sessionStatusText = document.getElementById("session_status_text");
const sessionTimer = document.getElementById("session_timer");
const sessionDurationInput = document.getElementById("session_duration");

let stream = null;
let sessionStarted = false;
let timerInterval = null;
let secondsRemaining = 0;

function formatTime(totalSeconds) {
    const minutes = String(Math.floor(totalSeconds / 60)).padStart(2, "0");
    const seconds = String(totalSeconds % 60).padStart(2, "0");
    return `${minutes}:${seconds}`;
}

function setInitialTimer() {
    const durationMinutes = parseInt(sessionDurationInput.value, 10) || 1;
    secondsRemaining = durationMinutes * 60;
    sessionTimer.textContent = formatTime(secondsRemaining);
}

function stopCountdown() {
    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
    }
}

function showPreSessionButtons() {
    enableMicButton.hidden = false;
    startButton.hidden = false;
    backButton.hidden = false;
    cancelButton.hidden = true;
}

function showActiveSessionButtons() {
    enableMicButton.hidden = true;
    startButton.hidden = true;
    backButton.hidden = true;
    cancelButton.hidden = false;
}

function startCountdown() {
    stopCountdown();
    setInitialTimer();

    timerInterval = setInterval(() => {
        secondsRemaining -= 1;

        if (secondsRemaining <= 0) {
            sessionTimer.textContent = "00:00";
            cancelSession();
            return;
        }

        sessionTimer.textContent = formatTime(secondsRemaining);
    }, 1000);
}

async function requestMicPermission() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        micStatus.textContent = "Microphone is not supported here.";
        return;
    }

    try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        micStatus.textContent = "Microphone ready.";
        startButton.disabled = false;
        enableMicButton.disabled = true;
    } catch (err) {
        if (err.name === "NotAllowedError") {
            micStatus.textContent = "Microphone permission was denied.";
        } else if (err.name === "NotFoundError") {
            micStatus.textContent = "No microphone was found.";
        } else {
            micStatus.textContent = "Could not access the microphone.";
        }

        startButton.disabled = true;
        console.error("Microphone error:", err);
    }
}

function beginSession() {
    if (!stream || sessionStarted) {
        return;
    }

    sessionStarted = true;
    sessionStatusBox.hidden = false;
    sessionStatusText.textContent = "Session in progress...";
    showActiveSessionButtons();
    startCountdown();
}

function cancelSession() {
    stopCountdown();
    sessionStarted = false;

    if (stream) {
        stream.getTracks().forEach(track => track.stop());
        stream = null;
    }

    window.location.href = "/dashboard";
}

if (sessionDurationInput && sessionTimer) {
    setInitialTimer();
}

showPreSessionButtons();

if (enableMicButton) {
    enableMicButton.addEventListener("click", requestMicPermission);
}

if (startButton) {
    startButton.addEventListener("click", beginSession);
}

if (cancelButton) {
    cancelButton.addEventListener("click", cancelSession);
}