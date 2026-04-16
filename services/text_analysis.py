"""
Deterministic text-analysis helpers for the Communication Mode scoring rubric.
No external NLP libraries — only Python stdlib + regex.
"""

import re
import math

# ── Stopwords (common English function words) ──────────────────────────────

STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "in", "on", "at", "to",
    "for", "of", "with", "by", "from", "is", "are", "was", "were", "be",
    "been", "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "shall", "may", "might", "must", "can",
    "that", "this", "these", "those", "it", "its", "i", "me", "my",
    "we", "us", "our", "you", "your", "he", "him", "his", "she", "her",
    "they", "them", "their", "what", "which", "who", "whom", "where",
    "when", "why", "how", "not", "no", "nor", "so", "too", "very",
    "just", "about", "up", "out", "then", "than", "also", "into",
    "over", "after", "before", "between", "under", "again", "there",
    "here", "all", "each", "every", "both", "few", "more", "most",
    "other", "some", "such", "only", "own", "same", "as", "while",
    "because", "until", "during", "through", "above", "below", "am",
}

FILLER_WORDS_SINGLE = {"um", "uh", "ah", "er", "hmm", "hm", "like"}
FILLER_PHRASES_MULTI = [
    "you know", "sort of", "kind of", "i mean", "basically",
    "actually", "literally", "right", "okay so",
]

TRANSITION_PHRASES = [
    "first", "next", "then", "for example", "because",
    "however", "finally", "overall",
]

# Tone cue lexicons per supported tone
TONE_CUE_MATCHES = {
    "Formal": [
        "therefore", "however", "moreover", "furthermore", "regarding",
        "consequently", "nevertheless", "additionally", "thus",
        "in conclusion", "in summary", "it is important",
    ],
    "Persuasive": [
        "should", "need to", "important", "benefit", "must",
        "convince", "because", "therefore", "essential",
        "critical", "strongly", "clearly", "without a doubt",
    ],
    "Casual": [
        "gonna", "wanna", "gotta", "pretty much", "stuff",
        "things", "cool", "awesome", "yeah", "hey", "guys",
    ],
}

TONE_CUE_CONFLICTS = {
    "Formal": [
        "gonna", "wanna", "gotta", "ain't", "yeah", "stuff",
        "cool", "awesome", "hey", "guys", "kinda", "sorta",
        "can't", "won't", "don't", "isn't", "aren't", "it's",
        "i'm", "we're", "they're", "you're",
    ],
    "Persuasive": [],
    "Casual": [
        "therefore", "moreover", "furthermore", "consequently",
        "nevertheless", "regarding", "additionally", "henceforth",
    ],
}


# ── Utility helpers ─────────────────────────────────────────────────────────

def clamp(x: float) -> float:
    """Clamp a value to [0, 100]."""
    return max(0.0, min(100.0, x))


def normalize_text(text: str) -> str:
    """Lowercase + trim text for simple lexical comparisons."""
    return text.lower().strip()


def tokenize_words(text: str) -> list:
    """Split text into lowercase word tokens (letters + apostrophes)."""
    return re.findall(r"[a-z']+", text.lower())


def content_words(tokens: list) -> list:
    """Return tokens that are not stopwords and are at least 2 chars."""
    return [t for t in tokens if t not in STOPWORDS and len(t) >= 2]


# ── Filler words ────────────────────────────────────────────────────────────

def count_filler_words(text: str) -> int:
    """
    Count hesitation language used in delivery-confidence scoring.

    Includes multi-word phrases (e.g., "you know") plus single-word fillers.
    """
    lower = text.lower()
    count = 0

    # Phrase-first pass avoids missing common conversational fillers.
    for phrase in FILLER_PHRASES_MULTI:
        occurrences = len(re.findall(r'\b' + re.escape(phrase) + r'\b', lower))
        count += occurrences

    # Token pass captures short fillers such as "um", "uh", and "like".
    tokens = tokenize_words(lower)
    for token in tokens:
        if token in FILLER_WORDS_SINGLE:
            count += 1

    return count


# ── Sentence splitting ──────────────────────────────────────────────────────

def split_sentences(text: str, words: list = None) -> list:
    """
    Split transcript into sentences.
    Primary: punctuation-based (.!?).
    Fallback: pause gaps > 1.2 s between words (if word timing available).
    """
    text = text.strip()
    if not text:
        return [text] if text else [""]

    # Punctuation split
    parts = re.split(r'(?<=[.!?])\s+', text)
    parts = [p.strip() for p in parts if p.strip()]

    if len(parts) >= 3:
        return parts

    # Fallback: pause-based splitting when word timing is available
    if words and len(words) >= 2:
        segments = []
        current = []
        for i, w in enumerate(words):
            current.append(w.get("text", ""))
            if i < len(words) - 1:
                gap = (words[i + 1].get("start", 0) - w.get("end", 0)) / 1000.0
                if gap > 1.2:
                    segments.append(" ".join(current))
                    current = []
        if current:
            segments.append(" ".join(current))

        if len(segments) >= 2:
            return segments

    return parts if parts else [text]


def sentence_lengths(sentences: list) -> list:
    """Convert sentence strings into token-count lengths."""
    return [len(tokenize_words(s)) for s in sentences]


# ── Statistics ──────────────────────────────────────────────────────────────

def stddev(values: list) -> float:
    """Population standard deviation used for sentence-length consistency."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return math.sqrt(variance)


# ── Topic keyword extraction ───────────────────────────────────────────────

def extract_topic_keywords(topic: str, min_keywords: int = 5,
                           max_keywords: int = 10) -> list:
    """
    Build a compact keyword set representing topic intent.

    Strategy:
    - keep informative unigrams
    - prioritize informative bigrams for context
    - pad with extra tokens when topic text is very short
    """
    tokens = re.findall(r"[a-z]+", topic.lower())
    informative = [t for t in tokens if t not in STOPWORDS and len(t) >= 3]

    bigrams = []
    for i in range(len(informative) - 1):
        bigrams.append(informative[i] + " " + informative[i + 1])

    combined = bigrams + informative
    seen = set()
    unique = []
    for kw in combined:
        if kw not in seen:
            seen.add(kw)
            unique.append(kw)

    # Prefer longer phrases first (bigrams)
    unique.sort(key=lambda x: -len(x))

    result = unique[:max_keywords]

    if len(result) < min_keywords:
        extra = [t for t in tokens if t not in STOPWORDS and len(t) >= 2
                 and t not in seen]
        for e in extra:
            if len(result) >= max_keywords:
                break
            result.append(e)
            seen.add(e)

    return result


# ── Keyword coverage ───────────────────────────────────────────────────────

def _simple_variants(word: str) -> list:
    """Generate simple singular/plural/close variants."""
    variants = [word]
    if word.endswith("s"):
        variants.append(word[:-1])
    else:
        variants.append(word + "s")
    if word.endswith("y"):
        variants.append(word[:-1] + "ies")
    if word.endswith("ies"):
        variants.append(word[:-3] + "y")
    if word.endswith("ing"):
        variants.append(word[:-3])
        variants.append(word[:-3] + "e")
    if word.endswith("ed"):
        variants.append(word[:-2])
        variants.append(word[:-1])
    if word.endswith("tion"):
        variants.append(word[:-4] + "te")
    return variants


def keyword_coverage(topic_keywords: list, transcript_text: str) -> tuple:
    """
    Estimate how much of the topic appears in transcript content.

    Counts a keyword as covered by exact phrase match or simple morphological
    variants of component words.
    """
    lower = transcript_text.lower()
    covered = 0
    total = len(topic_keywords)

    for kw in topic_keywords:
        kw_lower = kw.lower()
        if kw_lower in lower:
            covered += 1
            continue

        words_in_kw = kw_lower.split()
        found = False
        for w in words_in_kw:
            for variant in _simple_variants(w):
                if re.search(r'\b' + re.escape(variant) + r'\b', lower):
                    found = True
                    break
            if found:
                break
        if found:
            covered += 1

    return covered, total


# ── Tone alignment ─────────────────────────────────────────────────────────

def tone_alignment_score_parts(transcript_text: str, tone: str) -> tuple:
    """
    Count positive and conflicting lexical cues for selected tone.
    Returned tuple is consumed by relevance scoring.
    """
    lower = transcript_text.lower()
    matches = 0
    conflicts = 0

    for phrase in TONE_CUE_MATCHES.get(tone, []):
        if re.search(r'\b' + re.escape(phrase) + r'\b', lower):
            matches += 1

    for phrase in TONE_CUE_CONFLICTS.get(tone, []):
        if re.search(r'\b' + re.escape(phrase) + r'\b', lower):
            conflicts += 1

    return matches, conflicts


# ── Readability ─────────────────────────────────────────────────────────────

def estimate_syllables(word: str) -> int:
    """Approximate syllables for readability formulas."""
    word = word.lower().strip()
    if len(word) <= 2:
        return 1

    vowels = "aeiouy"
    count = 0
    prev_vowel = False

    for ch in word:
        is_vowel = ch in vowels
        if is_vowel and not prev_vowel:
            count += 1
        prev_vowel = is_vowel

    # Silent e at end
    if word.endswith("e") and count > 1:
        count -= 1

    return max(1, count)


def flesch_kincaid_grade(text: str) -> float:
    """
    Compute approximate Flesch-Kincaid grade level.
    Returns None for very short samples where readability is unreliable.
    """
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences:
        return None

    words = tokenize_words(text)
    if len(words) < 10:
        return None

    total_syllables = sum(estimate_syllables(w) for w in words)
    num_sentences = len(sentences)
    num_words = len(words)

    grade = (0.39 * (num_words / num_sentences)
             + 11.8 * (total_syllables / num_words)
             - 15.59)
    return round(grade, 1)


# ── Cosine similarity (pure Python) ────────────────────────────────────────

def cosine_similarity(vec_a: list, vec_b: list) -> float:
    if len(vec_a) != len(vec_b) or not vec_a:
        return 0.0

    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    mag_a = math.sqrt(sum(a * a for a in vec_a))
    mag_b = math.sqrt(sum(b * b for b in vec_b))

    if mag_a == 0.0 or mag_b == 0.0:
        return 0.0

    return dot / (mag_a * mag_b)
