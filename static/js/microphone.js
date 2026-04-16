const micStatus = document.getElementById("mic_status");
const enableMicButton = document.getElementById("enable_mic_btn");
const startButton = document.getElementById("start_session_btn");
const cancelButton = document.getElementById("cancel_session_btn");
const backButton = document.getElementById("back_to_dashboard_btn");
const sessionStatusBox = document.getElementById("session_status_box");
const sessionStatusText = document.getElementById("session_status_text");
const sessionTimer = document.getElementById("session_timer");
const sessionError = document.getElementById("session_error");

const sessionDurationInput = document.getElementById("session_duration");
const sessionTopicInput = document.getElementById("session_topic");
const sessionAudienceInput = document.getElementById("session_audience");
const sessionToneInput = document.getElementById("session_tone");

// Session lifecycle state shared across mic/start/countdown/upload steps.
let stream = null;
let mediaRecorder = null;
let recordedChunks = [];
let sessionStarted = false;
let timerInterval = null;
let secondsRemaining = 0;
let chosenMimeType = null;
let isProcessing = false;
let isCanceled = false;

function chooseSupportedMimeType() {
    // Browser-dependent fallback order to maximize MediaRecorder compatibility.
    const types = [
        "audio/webm;codecs=opus",
        "audio/webm",
        "audio/ogg;codecs=opus",
        "audio/mp4",
    ];
    for (const t of types) {
        if (MediaRecorder.isTypeSupported(t)) {
            return t;
        }
    }
    return null;
}

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

function stopMediaTracks() {
    if (stream) {
        stream.getTracks().forEach(function (track) { track.stop(); });
        stream = null;
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

function showProcessingState() {
    cancelButton.hidden = true;
    sessionStatusText.textContent = "Processing your session\u2026 This may take a little while.";
    sessionStatusBox.hidden = false;
    isProcessing = true;
}

function showError(message) {
    sessionError.textContent = message;
    sessionError.hidden = false;
}

function hideError() {
    sessionError.textContent = "";
    sessionError.hidden = true;
}

async function requestMicPermission() {
    // Explicitly request user permission before enabling recording controls.
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
    }
}

function beginSession() {
    if (!stream || sessionStarted) {
        return;
    }

    isCanceled = false;
    hideError();
    recordedChunks = [];
    chosenMimeType = chooseSupportedMimeType();

    var options = {};
    if (chosenMimeType) {
        options.mimeType = chosenMimeType;
    }

    try {
        // Use preferred MIME type when available; fallback keeps behavior stable.
        mediaRecorder = new MediaRecorder(stream, options);
    } catch (e) {
        mediaRecorder = new MediaRecorder(stream);
    }

    mediaRecorder.addEventListener("dataavailable", function (event) {
        // MediaRecorder emits chunks over time; store them for final Blob merge.
        if (event.data && event.data.size > 0) {
            recordedChunks.push(event.data);
        }
    });

    mediaRecorder.addEventListener("stop", function () {
        handleRecordingComplete();
    });

    mediaRecorder.start();
    sessionStarted = true;
    sessionStatusBox.hidden = false;
    sessionStatusText.textContent = "Recording in progress\u2026";
    showActiveSessionButtons();

    stopCountdown();
    setInitialTimer();

    timerInterval = setInterval(function () {
        secondsRemaining -= 1;

        if (secondsRemaining <= 0) {
            sessionTimer.textContent = "00:00";
            stopCountdown();
            sessionStatusText.textContent = "Recording complete. Processing\u2026";

            if (mediaRecorder && mediaRecorder.state !== "inactive") {
                mediaRecorder.stop();
            }
            // Stop hardware capture once recording window ends.
            stopMediaTracks();
            return;
        }

        sessionTimer.textContent = formatTime(secondsRemaining);
    }, 1000);
}

function handleRecordingComplete() {
    if (isCanceled) {
        return;
    }

    if (recordedChunks.length === 0) {
        showError("No audio was recorded. Please try again.");
        showPreSessionButtons();
        sessionStarted = false;
        return;
    }

    // Build one uploadable file from recorded MediaRecorder chunks.
    var mimeForBlob = chosenMimeType || "audio/webm";
    var blob = new Blob(recordedChunks, { type: mimeForBlob });

    if (blob.size === 0) {
        showError("Recording is empty. Please try again.");
        showPreSessionButtons();
        sessionStarted = false;
        return;
    }

    showProcessingState();
    uploadCompletedSession(blob, mimeForBlob);
}

async function uploadCompletedSession(blob, mimeType) {
    // Keep extension aligned with recorded MIME so backend can map correctly.
    var ext = ".webm";
    if (mimeType.indexOf("ogg") !== -1) ext = ".ogg";
    else if (mimeType.indexOf("mp4") !== -1) ext = ".mp4";

    var filename = "session_" + Date.now() + ext;

    // POST multipart payload expected by /complete-session route.
    // Includes immutable setup values plus the recorded audio blob.
    var formData = new FormData();
    formData.append("audio", blob, filename);
    formData.append("topic", sessionTopicInput.value);
    formData.append("audience", sessionAudienceInput.value);
    formData.append("tone", sessionToneInput.value);
    formData.append("duration", sessionDurationInput.value);

    try {
        var response = await fetch("/complete-session", {
            method: "POST",
            body: formData,
        });

        var data = await response.json();

        if (data.success) {
            // Backend returns session_id for results lookup and page redirect.
            window.location.href = "/results?session_id=" + data.session_id;
        } else {
            showError(data.error || "Something went wrong. Please try again.");
            showPreSessionButtons();
            sessionStarted = false;
            isProcessing = false;
        }
    } catch (err) {
        showError("Network error. Please check your connection and try again.");
        showPreSessionButtons();
        sessionStarted = false;
        isProcessing = false;
    }
}

function cancelSession() {
    // Cancel abandons upload and returns to dashboard immediately.
    isCanceled = true;
    stopCountdown();

    if (mediaRecorder && mediaRecorder.state !== "inactive") {
        mediaRecorder.stop();
    }

    stopMediaTracks();
    sessionStarted = false;
    recordedChunks = [];
    window.location.href = "/dashboard";
}

// ── Initialization ─────────────────────────────────────────────────────────

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
