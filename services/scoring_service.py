"""
Communication Mode scoring rubric implementation.
All numeric scores are computed here in Flask — no LLM decides the numbers.
"""

from services.text_analysis import (
    clamp, tokenize_words, content_words, count_filler_words,
    split_sentences, sentence_lengths, stddev,
    extract_topic_keywords, keyword_coverage,
    tone_alignment_score_parts, flesch_kincaid_grade,
    TRANSITION_PHRASES,
)
from services.cohere_service import embed_topic_and_transcript

import re


# ── Audience grade-level target ranges ──────────────────────────────────────

AUDIENCE_GRADE_RANGES = {
    "Kids": (3, 6),
    "General": (7, 10),
    "Professional": (10, 14),
}


# ── Base metrics builder ───────────────────────────────────────────────────

def build_base_metrics(topic: str, audience: str, tone: str,
                       transcript_payload: dict) -> dict:
    """
    Compute every shared metric from the transcript payload once,
    so individual rubric functions can reuse them.
    """
    text = transcript_payload.get("text", "") or ""
    words = transcript_payload.get("words", [])
    overall_confidence = transcript_payload.get("confidence", 0.0)

    tokens = tokenize_words(text)
    total_words = len(tokens)

    # Speaking duration from word timestamps
    if words:
        first_start = words[0].get("start", 0)
        last_end = words[-1].get("end", 0)
        speaking_ms = last_end - first_start
    else:
        speaking_ms = 0

    speaking_seconds = speaking_ms / 1000.0
    speaking_minutes = speaking_seconds / 60.0 if speaking_seconds > 0 else 0.001

    # Average word confidence
    if words:
        confs = [w.get("confidence", 0.0) for w in words]
        avg_word_confidence = sum(confs) / len(confs)
    elif overall_confidence:
        avg_word_confidence = overall_confidence
    else:
        avg_word_confidence = 0.85

    # Pause gaps between consecutive words
    gaps = []
    for i in range(1, len(words)):
        gap_ms = words[i].get("start", 0) - words[i - 1].get("end", 0)
        gaps.append(gap_ms / 1000.0)

    # Clarity long pauses (> 1.2 s)
    clarity_long_pauses = [g for g in gaps if g > 1.2]
    clarity_long_pause_count = len(clarity_long_pauses)
    clarity_long_pause_seconds = sum(clarity_long_pauses)

    # Confidence: hesitation pauses (0.8–1.5 s) and long pauses (> 1.5 s)
    hesitation_pauses = [g for g in gaps if 0.8 <= g <= 1.5]
    confidence_long_pauses = [g for g in gaps if g > 1.5]
    hesitation_count = len(hesitation_pauses)
    confidence_long_pause_count = len(confidence_long_pauses)

    # WPM
    wpm = total_words / speaking_minutes if speaking_minutes > 0 else 0

    # Filler words
    filler_count = count_filler_words(text)

    # Continuous speech segments (split at gaps > 0.8 s)
    speech_segments = []
    seg_start = None
    for i, w in enumerate(words):
        if seg_start is None:
            seg_start = w.get("start", 0)
        if i < len(words) - 1:
            gap = (words[i + 1].get("start", 0) - w.get("end", 0)) / 1000.0
            if gap > 0.8:
                seg_end = w.get("end", 0)
                speech_segments.append((seg_end - seg_start) / 1000.0)
                seg_start = None
        else:
            seg_end = w.get("end", 0)
            speech_segments.append((seg_end - seg_start) / 1000.0)

    avg_speech_segment = (
        sum(speech_segments) / len(speech_segments) if speech_segments else 0.0
    )

    # Sentences
    sentences = split_sentences(text, words)
    total_sentences = len(sentences)
    sent_lens = sentence_lengths(sentences)
    avg_sentence_length = (
        sum(sent_lens) / len(sent_lens) if sent_lens else 0
    )
    sent_len_stddev = stddev([float(x) for x in sent_lens])

    # Transitions
    lower_text = text.lower()
    transition_count = 0
    for phrase in TRANSITION_PHRASES:
        transition_count += len(
            re.findall(r'\b' + re.escape(phrase) + r'\b', lower_text)
        )

    # Topic keywords + coverage
    topic_kws = extract_topic_keywords(topic)
    covered_kw, total_kw = keyword_coverage(topic_kws, text)
    kw_ratio = covered_kw / max(total_kw, 1)

    # Tone
    tone_matches, tone_conflicts = tone_alignment_score_parts(text, tone)

    # Readability
    grade = flesch_kincaid_grade(text)

    # Vocabulary metrics
    c_words = content_words(tokens)
    unique_content = set(c_words)
    total_content = len(c_words)
    lexical_diversity = len(unique_content) / max(total_content, 1)

    # Repeated non-stopwords: content words that appear > 2 times
    from collections import Counter
    cw_counts = Counter(c_words)
    repeated = sum(1 for w, c in cw_counts.items() if c > 2)

    return {
        "transcript_text": text,
        "words": words,
        "total_words": total_words,
        "speaking_seconds": round(speaking_seconds, 2),
        "speaking_minutes": round(speaking_minutes, 4),
        "average_word_confidence": round(avg_word_confidence, 4),
        "wpm": round(wpm, 1),
        "gaps": gaps,
        "clarity_long_pauses": clarity_long_pause_count,
        "clarity_long_pause_seconds": round(clarity_long_pause_seconds, 2),
        "confidence_hesitation_pauses": hesitation_count,
        "confidence_long_pauses": confidence_long_pause_count,
        "total_long_pause_seconds": round(
            clarity_long_pause_seconds + sum(confidence_long_pauses), 2
        ),
        "average_speech_segment_length": round(avg_speech_segment, 2),
        "filler_words": filler_count,
        "transition_phrases": transition_count,
        "sentences": sentences,
        "total_sentences": total_sentences,
        "average_sentence_length": round(avg_sentence_length, 1),
        "sentence_length_stddev": round(sent_len_stddev, 2),
        "topic_keywords": topic_kws,
        "covered_topic_keywords": covered_kw,
        "total_topic_keywords": total_kw,
        "keyword_coverage_ratio": round(kw_ratio, 4),
        "tone_matches": tone_matches,
        "tone_conflicts": tone_conflicts,
        "readability_grade": grade,
        "unique_content_words": len(unique_content),
        "total_content_words": total_content,
        "repeated_non_stopwords": repeated,
        "lexical_diversity": round(lexical_diversity, 4),
        "audience": audience,
        "tone": tone,
    }


# ── Individual rubric scorers ──────────────────────────────────────────────

def score_clarity(m: dict) -> float:
    A = m["average_word_confidence"]
    speaking_min = m["speaking_minutes"]

    wpm = m["wpm"]
    lpm = m["clarity_long_pauses"] / speaking_min if speaking_min > 0 else 0
    alpd = (m["clarity_long_pause_seconds"]
            / max(m["clarity_long_pauses"], 1))

    intelligibility = 100 * A
    pace = clamp(100 - 2 * abs(wpm - 140))
    long_pause_control = clamp(100 * (1 - lpm / 6))
    pause_duration_control = clamp(100 * (1 - max(alpd - 1.2, 0) / 2.0))

    return (0.40 * intelligibility
            + 0.30 * pace
            + 0.20 * long_pause_control
            + 0.10 * pause_duration_control)


def score_confidence(m: dict) -> float:
    total_words = max(m["total_words"], 1)
    speaking_min = m["speaking_minutes"]

    f100 = m["filler_words"] * 100 / total_words
    hpm = m["confidence_hesitation_pauses"] / speaking_min if speaking_min > 0 else 0
    lpm = m["confidence_long_pauses"] / speaking_min if speaking_min > 0 else 0
    asl = m["average_speech_segment_length"]

    filler_score = clamp(100 * (1 - f100 / 8))
    hesitation_score = clamp(100 * (1 - hpm / 12))
    long_pause_score = clamp(100 * (1 - lpm / 6))
    continuity_score = clamp(100 * (asl / 12))

    return (0.45 * filler_score
            + 0.25 * hesitation_score
            + 0.20 * long_pause_score
            + 0.10 * continuity_score)


def score_structure(m: dict) -> float:
    total_words = max(m["total_words"], 1)
    total_sentences = max(m["total_sentences"], 1)

    tp100 = m["transition_phrases"] * 100 / total_words
    s = m["total_sentences"]
    avg_s = total_words / total_sentences
    slsd = m["sentence_length_stddev"]

    transition_score = clamp(100 * (tp100 / 3))
    sentence_count_score = clamp(100 * (s / 6))
    sentence_length_balance = clamp(100 - 4 * abs(avg_s - 18))
    sentence_consistency = clamp(100 - 2 * slsd)

    return (0.50 * transition_score
            + 0.20 * sentence_count_score
            + 0.20 * sentence_length_balance
            + 0.10 * sentence_consistency)


def score_relevance(m: dict, similarity: float) -> float:
    kc = m["keyword_coverage_ratio"]
    tone_total = m["tone_matches"] + m["tone_conflicts"]
    ta = m["tone_matches"] / max(tone_total, 1)

    prompt_sim = 100 * similarity
    kw_cov = 100 * kc
    tone_align = 100 * ta

    # Fallbacks
    if not m["topic_keywords"]:
        kw_cov = prompt_sim
    if m["tone"] not in ("Formal", "Persuasive", "Casual"):
        tone_align = 100

    return (0.55 * prompt_sim
            + 0.35 * kw_cov
            + 0.10 * tone_align)


def score_vocabulary(m: dict) -> float:
    ld = m["lexical_diversity"]
    total_words = max(m["total_words"], 1)
    rep100 = m["repeated_non_stopwords"] * 100 / total_words
    grade = m["readability_grade"]
    audience = m["audience"]

    low, high = AUDIENCE_GRADE_RANGES.get(audience, (7, 10))

    if grade is not None:
        if grade < low:
            dist = low - grade
        elif grade > high:
            dist = grade - high
        else:
            dist = 0
    else:
        dist = 0

    lexical_div = clamp(100 * (ld / 0.60))
    repetition_ctrl = clamp(100 * (1 - rep100 / 20))
    audience_fit = clamp(100 - 20 * dist)

    return (0.40 * lexical_div
            + 0.25 * repetition_ctrl
            + 0.35 * audience_fit)


# ── Main orchestrator ──────────────────────────────────────────────────────

def score_communication_session(
    topic: str,
    audience: str,
    tone: str,
    duration_minutes: int,
    transcript_payload: dict,
) -> dict:
    """
    Compute all rubric scores and return a complete result dict.
    """
    m = build_base_metrics(topic, audience, tone, transcript_payload)

    low_sample_flags = []
    if m["total_words"] < 20:
        low_sample_flags.append("very_short_transcript")
    if m["speaking_seconds"] < 15:
        low_sample_flags.append("very_short_duration")

    # Cohere embeddings for relevance (with fallback)
    try:
        similarity = embed_topic_and_transcript(topic, m["transcript_text"])
    except Exception:
        similarity = m["keyword_coverage_ratio"]

    clarity = score_clarity(m)
    confidence = score_confidence(m)
    structure = score_structure(m)
    relevance = score_relevance(m, similarity)
    vocabulary = score_vocabulary(m)

    overall = (
        clarity * 0.30
        + confidence * 0.20
        + structure * 0.20
        + relevance * 0.20
        + vocabulary * 0.10
    )

    # Build raw_metrics for storage/debugging (exclude non-serialisable data)
    raw_metrics = {
        "total_words": m["total_words"],
        "speaking_seconds": m["speaking_seconds"],
        "speaking_minutes": m["speaking_minutes"],
        "average_word_confidence": m["average_word_confidence"],
        "wpm": m["wpm"],
        "clarity_long_pauses": m["clarity_long_pauses"],
        "clarity_long_pause_seconds": m["clarity_long_pause_seconds"],
        "confidence_hesitation_pauses": m["confidence_hesitation_pauses"],
        "confidence_long_pauses": m["confidence_long_pauses"],
        "average_speech_segment_length": m["average_speech_segment_length"],
        "filler_words": m["filler_words"],
        "transition_phrases": m["transition_phrases"],
        "total_sentences": m["total_sentences"],
        "average_sentence_length": m["average_sentence_length"],
        "sentence_length_stddev": m["sentence_length_stddev"],
        "topic_keywords": m["topic_keywords"],
        "covered_topic_keywords": m["covered_topic_keywords"],
        "keyword_coverage_ratio": m["keyword_coverage_ratio"],
        "tone_matches": m["tone_matches"],
        "tone_conflicts": m["tone_conflicts"],
        "readability_grade": m["readability_grade"],
        "unique_content_words": m["unique_content_words"],
        "total_content_words": m["total_content_words"],
        "repeated_non_stopwords": m["repeated_non_stopwords"],
        "lexical_diversity": m["lexical_diversity"],
        "cohere_similarity": round(similarity, 4),
        "low_sample_flags": low_sample_flags,
    }

    return {
        "overall_score": round(overall),
        "clarity": round(clarity),
        "confidence": round(confidence),
        "structure": round(structure),
        "relevance": round(relevance),
        "vocabulary": round(vocabulary),
        "transcript_text": m["transcript_text"],
        "raw_metrics": raw_metrics,
        "low_sample_flags": low_sample_flags,
    }
