"""
AssemblyAI transcription via direct REST calls (no SDK).
Upload → create transcript → poll until complete → return normalized result.
"""

import time
import requests

BASE_URL = "https://api.assemblyai.com"


def upload_audio_to_assemblyai(file_path: str, api_key: str) -> str:
    """Upload a local audio file to AssemblyAI and return the upload URL."""
    headers = {"authorization": api_key}

    with open(file_path, "rb") as f:
        response = requests.post(
            f"{BASE_URL}/v2/upload",
            headers=headers,
            data=f,
        )

    response.raise_for_status()
    return response.json()["upload_url"]


def submit_transcription_job(upload_url: str, api_key: str) -> str:
    """Submit a transcription job and return the transcript ID."""
    headers = {
        "authorization": api_key,
        "content-type": "application/json",
    }
    payload = {
        "audio_url": upload_url,
        "speech_models": ["universal-3-pro", "universal-2"],
        "language_detection": True,
    }

    response = requests.post(
        f"{BASE_URL}/v2/transcript",
        headers=headers,
        json=payload,
    )
    response.raise_for_status()
    return response.json()["id"]


def poll_transcription_result(transcript_id: str, api_key: str,
                              poll_interval: int = 3,
                              max_wait_seconds: int = 300) -> dict:
    """Poll until the transcript is completed or an error occurs."""
    headers = {"authorization": api_key}
    url = f"{BASE_URL}/v2/transcript/{transcript_id}"
    elapsed = 0

    while elapsed < max_wait_seconds:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        status = data.get("status")
        if status == "completed":
            return data
        if status == "error":
            raise RuntimeError(
                f"AssemblyAI transcription failed: {data.get('error', 'unknown')}"
            )

        time.sleep(poll_interval)
        elapsed += poll_interval

    raise TimeoutError(
        f"Transcription not completed within {max_wait_seconds} seconds"
    )


def transcribe_audio_file(file_path: str, api_key: str) -> dict:
    """
    End-to-end transcription: upload → submit → poll → normalize.
    Returns a dict with text, confidence, words list, status, and raw_response.
    """
    upload_url = upload_audio_to_assemblyai(file_path, api_key)
    transcript_id = submit_transcription_job(upload_url, api_key)
    raw = poll_transcription_result(transcript_id, api_key)

    words = []
    for w in (raw.get("words") or []):
        words.append({
            "text": w.get("text", ""),
            "start": w.get("start", 0),
            "end": w.get("end", 0),
            "confidence": w.get("confidence", 0.0),
        })

    return {
        "text": raw.get("text", "") or "",
        "confidence": raw.get("confidence", 0.0) or 0.0,
        "words": words,
        "status": "completed",
        "raw_response": raw,
    }
