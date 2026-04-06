const com_form = document.getElementById('com_form');

const mic_status = document.getElementById('mic_status');       // html file should have <p id="mic_status"></p> somewhere on the page

async function requestMicPermission() {         // Function handles the microphone permissions
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        if (mic_status) {
            mic_status.textContent = 'Microphone is not supported here.';
        }
        return false;
    }

    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

        stream.getTracks().forEach(track => track.stop());
        return true;
    } 
    
    catch (err) {
        if (mic_status) {
            if (err.name === 'NotAllowedError') {
                mic_status.textContent = 'Microphone permission was denied.';
            } 
            
            else if (err.name === 'NotFoundError') {
                mic_status.textContent = 'No microphone was found.';
            } 
            
            else {
                mic_status.textContent = 'Could not access the microphone.';
            }
        }

        console.error('Microphone error:', err);
        return false;
    }
}

