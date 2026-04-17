"""
This file handles:

- connecting to the Cohere API
- checking how relevant the transcript is to the topic
- generating structured AI feedback for the session
- returning fallback feedback if Cohere fails
"""

import os
import json
import cohere
from services.text_analysis import cosine_similarity


def get_cohere_client():
    """Create Cohere client from API key."""
    return cohere.ClientV2(api_key=os.getenv("COHERE_API_KEY"))


# Embeddings for relevance --------------------------------------------------

def embed_topic_and_transcript(topic: str, transcript: str) -> float:
    """
    Turn the topic and transcript into embeddings and return
    how similar they are as a number from 0.0 to 1.0.
    """
    client = get_cohere_client()

    # Treat the topic like a search query.
    topic_resp = client.embed(
        model="embed-v4.0",
        input_type="search_query",
        embedding_types=["float"],
        inputs=[{"content": [{"type": "text", "text": topic}]}],
        output_dimension=1024,
    )

    # Treat the transcript like a document.
    # Only use the first 2048 characters to keep it manageable.
    transcript_resp = client.embed(
        model="embed-v4.0",
        input_type="search_document",
        embedding_types=["float"],
        inputs=[{"content": [{"type": "text", "text": transcript[:2048]}]}],
        output_dimension=1024,
    )

    topic_vec = topic_resp.embeddings.float_[0]
    transcript_vec = transcript_resp.embeddings.float_[0]

    sim = cosine_similarity(list(topic_vec), list(transcript_vec))
    return max(0.0, min(1.0, sim))


# Structured feedback generation ----------------------------------------------

FEEDBACK_SCHEMA = {
    "type": "object",
    "properties": {
        "overall_feedback": {"type": "string"},
        "clarity_feedback": {"type": "string"},
        "confidence_feedback": {"type": "string"},
        "structure_feedback": {"type": "string"},
        "relevance_feedback": {"type": "string"},
        "vocabulary_feedback": {"type": "string"},
        "strengths": {"type": "array", "items": {"type": "string"}},
        "improvements": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "overall_feedback", "clarity_feedback", "confidence_feedback",
        "structure_feedback", "relevance_feedback", "vocabulary_feedback",
        "strengths", "improvements",
    ],
}


def generate_feedback_json(
    topic: str,
    audience: str,
    tone: str,
    duration: int,
    transcript_text: str,
    scores: dict,
    raw_metrics: dict,
    low_sample_flags: list,
) -> dict:
    """
    Ask Cohere for structured JSON feedback about the session.

    Deterministic fallback exists to guarantee the app still returns valid
    feedback if Cohere is unavailable or returns malformed output.
    """
    try:
        return _call_cohere_feedback(
            topic, audience, tone, duration, transcript_text,
            scores, raw_metrics, low_sample_flags,
        )
    except Exception:
        return _deterministic_fallback(scores, topic, audience, tone)


def _call_cohere_feedback(
    topic, audience, tone, duration, transcript_text,
    scores, raw_metrics, low_sample_flags,) -> dict:
    
    client = get_cohere_client()

    flags_note = ""
    if low_sample_flags:
        flags_note = (
            "\nNote: the recording was short so some metrics have low confidence. "
            f"Flags: {', '.join(low_sample_flags)}. "
            "Keep feedback encouraging despite limited data."
        )

    # Prompt includes rubric scores + key metrics so generated comments align
    # with deterministic scoring decisions already computed in Flask.
    prompt = f"""You are a speech-coaching assistant for a university course project.

A student just completed a {duration}-minute communication session.
Topic: "{topic}"
Target audience: {audience}
Desired tone: {tone}

Transcript (first 1500 chars):
\"\"\"{transcript_text[:1500]}\"\"\"

Numeric scores (0-100):
- Clarity: {scores.get('clarity', 0)}
- Confidence: {scores.get('confidence', 0)}
- Structure: {scores.get('structure', 0)}
- Relevance: {scores.get('relevance', 0)}
- Vocabulary: {scores.get('vocabulary', 0)}
- Overall: {scores.get('overall_score', 0)}

Key metrics:
- Words per minute: {raw_metrics.get('wpm', 'N/A')}
- Filler words: {raw_metrics.get('filler_words', 'N/A')}
- Transition phrases: {raw_metrics.get('transition_phrases', 'N/A')}
- Lexical diversity: {raw_metrics.get('lexical_diversity', 'N/A')}
{flags_note}

Return JSON only. Provide concise, encouraging, student-friendly feedback.
Each feedback field should be 1-3 sentences. Strengths and improvements should each have 2-3 items."""

    # Request strict JSON object output to match template expectations.
    response = client.chat(
        model="command-a-03-2025",
        messages=[{"role": "user", "content": prompt}],
        response_format={
            "type": "json_object",
            "json_schema": {
                "name": "session_feedback",
                "schema": FEEDBACK_SCHEMA,
            },
        },
    )

    text = response.message.content[0].text
    parsed = json.loads(text)

    # Validate all required keys before returning to route.
    for key in FEEDBACK_SCHEMA["required"]:
        if key not in parsed:
            raise ValueError(f"Missing key: {key}")

    return parsed


# Deterministic fallback -----------------------------------------------------------------------

def _score_comment(name: str, score: int) -> str:
    if score >= 85:
        return f"Your {name} was strong. Keep refining small details for even better results."
    if score >= 65:
        return f"Your {name} was solid but has room for improvement. Focus on consistency."
    return f"Your {name} needs work. Practice targeted exercises to build this skill."


def _deterministic_fallback(scores: dict, topic: str,
                            audience: str, tone: str) -> dict:
    """
    Build feedback from numeric rubric scores only.
    Ensures '/complete-session' can succeed even when Cohere fails.
    """
    overall = scores.get("overall_score", 0)

    if overall >= 80:
        overall_fb = (
            f"Good job on your session about '{topic}'! "
            "You demonstrated solid communication skills overall."
        )
    elif overall >= 60:
        overall_fb = (
            f"Decent effort on '{topic}'. "
            "There are a few areas where focused practice will help you improve."
        )
    else:
        overall_fb = (
            f"This session on '{topic}' shows you're still building your skills. "
            "Don't worry — practice makes a big difference."
        )

    strengths = []
    improvements = []
    for name in ["clarity", "confidence", "structure", "relevance", "vocabulary"]:
        s = scores.get(name, 0)
        if s >= 75:
            strengths.append(f"{name.capitalize()} ({s}/100)")
        else:
            improvements.append(f"Work on {name} (scored {s}/100)")

    if not strengths:
        strengths = ["You completed the full session — that takes effort!"]
    if not improvements:
        improvements = ["Keep practicing to maintain your high scores."]

    return {
        "overall_feedback": overall_fb,
        "clarity_feedback": _score_comment("clarity", scores.get("clarity", 0)),
        "confidence_feedback": _score_comment("confidence", scores.get("confidence", 0)),
        "structure_feedback": _score_comment("structure", scores.get("structure", 0)),
        "relevance_feedback": _score_comment("relevance", scores.get("relevance", 0)),
        "vocabulary_feedback": _score_comment("vocabulary", scores.get("vocabulary", 0)),
        "strengths": strengths[:3],
        "improvements": improvements[:3],
    }
