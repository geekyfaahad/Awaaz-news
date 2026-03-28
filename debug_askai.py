"""Debug the Ask AI pipeline to find the crash."""
import re
import os
import sys
import traceback
from pathlib import Path
from urllib.parse import urlencode
import xml.etree.ElementTree as ET
import requests

# Load .env
env_path = Path(__file__).resolve().parent / ".env"
if env_path.is_file():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, val)

GOOGLE_NEWS_RSS_BASE = "https://news.google.com/rss/search"

# Copy the exact stop-words set from app.py
_X_STOP_WORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "shall",
    "should", "may", "might", "must", "can", "could", "about", "above",
    "after", "again", "against", "all", "am", "and", "any", "at", "because",
    "before", "below", "between", "both", "but", "by", "down", "during",
    "each", "few", "for", "from", "further", "get", "got", "he", "her",
    "here", "hers", "herself", "him", "himself", "his", "how", "i", "if",
    "in", "into", "it", "its", "itself", "just", "me", "meets", "met",
    "more", "most", "my", "myself", "no", "nor", "not", "now", "of", "off",
    "on", "once", "only", "or", "other", "our", "ours", "ourselves", "out",
    "over", "own", "re", "same", "she", "so", "some", "such", "than",
    "that", "their", "theirs", "them", "themselves", "then", "there",
    "these", "they", "this", "those", "through", "to", "too", "under",
    "until", "up", "very", "we", "what", "when", "where", "which", "while",
    "who", "whom", "why", "with", "you", "your", "yours", "yourself",
    "delegation", "reportedly", "allegedly", "says", "said", "told",
    "according", "visit", "visits", "visiting", "visited",
    "news", "article", "headline", "spam", "fake", "check", "real",
    "true", "false", "whether", "please", "tell", "know",
})

_NEGATIVE_ACTION_WORDS = frozenset({
    "killed", "dead", "died", "dies", "death", "murder", "murdered",
    "assassinated", "shot", "shooting", "arrested", "detained", "kidnapped",
    "attacked", "injured", "bomb", "bombed", "explosion", "blast",
    "resign", "resigned", "resigns", "sacked", "fired", "suspended",
    "missing", "crash", "collapsed", "suicide",
})

_COMMENTARY_VERBS = frozenset({
    "questions", "condemns", "slams", "demands", "seeks", "says", "said",
    "asks", "urges", "calls", "criticizes", "criticises", "warns",
    "reacts", "responds", "mourns", "condoles", "appeals", "addresses",
    "discusses", "speaks", "tweets", "posts", "comments", "hails",
    "welcomes", "praises", "salutes", "lauds", "supports", "opposes",
    "denies", "refutes", "clarifies", "announces", "declares",
    "orders", "directs", "reviews", "meets", "visits", "inaugurates",
})

_SERIOUS_CLAIM_BRIDGE_WORDS = frozenset({
    "is", "was", "were", "has", "have", "had", "been", "being", "be",
    "found", "confirmed", "reportedly", "reported", "declared",
    "officially", "now", "feared",
})

_NEGATION_OR_RUMOR_CUES = frozenset({
    "no", "not", "fake", "false", "hoax", "rumor", "rumour",
    "rumors", "rumours", "debunk", "debunked", "debunks", "denies",
    "deny", "denied", "alive", "safe", "unharmed",
})


def _tokenize_lower(text):
    return re.findall(r"[a-z0-9']+", (text or "").lower())


def _extract_claim_subject_tokens(claim_tokens):
    seen = set()
    subject_tokens = []
    for token in claim_tokens:
        if token in _NEGATIVE_ACTION_WORDS or token in _X_STOP_WORDS or len(token) <= 2 or token in seen:
            continue
        seen.add(token)
        subject_tokens.append(token)
    return subject_tokens


def _find_subject_spans(claim_subjects, headline_tokens):
    if not claim_subjects or not headline_tokens:
        return []

    unique_subjects = list(dict.fromkeys(claim_subjects))
    required_matches = 1 if len(unique_subjects) == 1 else 2
    spans = []

    for start in range(len(headline_tokens)):
        if headline_tokens[start] != unique_subjects[0]:
            continue

        matched = 1
        last_pos = start
        for token in unique_subjects[1:]:
            found_pos = None
            for pos in range(last_pos + 1, min(len(headline_tokens), last_pos + 3)):
                if headline_tokens[pos] == token:
                    found_pos = pos
                    break
            if found_pos is None:
                break
            matched += 1
            last_pos = found_pos

        if matched >= required_matches:
            spans.append((start, last_pos))

    return spans


def _check_subject_action_alignment(claim_subjects, claim_actions, headline_tokens, headline_actions):
    if not claim_subjects or not headline_tokens:
        return False
    subject_spans = _find_subject_spans(claim_subjects, headline_tokens)
    action_positions = [i for i, t in enumerate(headline_tokens) if t in headline_actions]
    if not action_positions or not subject_spans:
        return False
    for act_pos in action_positions:
        for span_start, span_end in subject_spans:
            if span_end < act_pos:
                bridge = headline_tokens[span_end + 1:act_pos]
                if len(bridge) <= 2 and all(t in _SERIOUS_CLAIM_BRIDGE_WORDS for t in bridge):
                    return True
            if act_pos < span_start:
                if act_pos + 1 >= len(headline_tokens) or headline_tokens[act_pos + 1] != "of":
                    continue
                bridge = headline_tokens[act_pos + 2:span_start]
                if len(bridge) <= 2 and all(t in _SERIOUS_CLAIM_BRIDGE_WORDS for t in bridge):
                    return True
    return False


def _headline_negates_claim(claim_subjects, headline_tokens, headline_actions):
    if not claim_subjects or not headline_tokens:
        return False

    subject_spans = _find_subject_spans(claim_subjects, headline_tokens)
    if not subject_spans:
        return False

    negation_positions = [i for i, t in enumerate(headline_tokens) if t in _NEGATION_OR_RUMOR_CUES]
    if not negation_positions:
        return False

    action_positions = [i for i, t in enumerate(headline_tokens) if t in headline_actions] if headline_actions else []

    for span_start, span_end in subject_spans:
        context_start = max(0, span_start - 4)
        context_end = min(len(headline_tokens), span_end + 5)
        if any(context_start <= pos < context_end for pos in negation_positions):
            return True

        for act_pos in action_positions:
            context_start = max(0, min(span_start, act_pos) - 3)
            context_end = min(len(headline_tokens), max(span_end, act_pos) + 4)
            if any(context_start <= pos < context_end for pos in negation_positions):
                return True

    return False


def _semantic_verify_claim(user_claim, headlines):
    claim_tokens = _tokenize_lower(user_claim)
    if not claim_tokens or not headlines:
        return {"verified": False, "confidence": "low", "reason": "Insufficient data.", "matching_headlines": []}

    claim_set = set(claim_tokens)
    claim_action_words = claim_set & _NEGATIVE_ACTION_WORDS
    has_serious_claim = bool(claim_action_words)
    claim_subject_tokens = _extract_claim_subject_tokens(claim_tokens)

    matching, contradicting, neutral = [], [], []

    for idx, item in enumerate(headlines):
        title = item.get("title") or ""
        title_tokens = _tokenize_lower(title)
        title_set = set(title_tokens)
        overlap = claim_set & title_set
        overlap_ratio = len(overlap) / max(len(claim_set), 1)

        if overlap_ratio < 0.3:
            neutral.append(idx)
            continue

        if has_serious_claim:
            headline_actions = title_set & _NEGATIVE_ACTION_WORDS
            headline_commentary = title_set & _COMMENTARY_VERBS

            if headline_actions:
                action_subject_match = _check_subject_action_alignment(
                    claim_subject_tokens, claim_action_words,
                    title_tokens, headline_actions
                )
                negates_claim = _headline_negates_claim(claim_subject_tokens, title_tokens, headline_actions)
                if action_subject_match and not negates_claim:
                    matching.append(idx)
                else:
                    contradicting.append(idx)
            elif headline_commentary or _headline_negates_claim(claim_subject_tokens, title_tokens, set()):
                contradicting.append(idx)
            else:
                neutral.append(idx)
        else:
            if overlap_ratio >= 0.5:
                matching.append(idx)
            else:
                neutral.append(idx)

    if matching:
        return {"verified": True, "confidence": "high" if len(matching) >= 2 else "medium",
                "reason": f"{len(matching)} headline(s) semantically match the claim.", "matching_headlines": matching}
    if contradicting and not matching:
        return {"verified": False, "confidence": "high" if has_serious_claim else "medium",
                "reason": "Headlines contain the same names/keywords but describe a DIFFERENT event. "
                          "The subject in the headlines is NOT the target of the claimed action.",
                "matching_headlines": []}
    return {"verified": False, "confidence": "low", "reason": "No headlines clearly confirm or deny this claim.",
            "matching_headlines": []}


# ── Step 1: Fetch Google News RSS ──
print("=" * 60)
query = "is omar abdullah dead?"
search_q = re.sub(r"\s+", " ", query.strip())[:450].strip()
print(f"Step 1: Search query = '{search_q}'")

rss_url = GOOGLE_NEWS_RSS_BASE + "?" + urlencode({"q": search_q, "hl": "en", "gl": "IN", "ceid": "IN:en"})
print(f"RSS URL: {rss_url}")

try:
    r = requests.get(rss_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=28)
    print(f"HTTP Status: {r.status_code}")
    root = ET.fromstring(r.text)
    items = []
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        source_el = item.find("source")
        source_name = (source_el.text or "").strip() if source_el is not None else ""
        if not title:
            continue
        low = title.lower()
        if low.startswith(("page", "page-", "page ")) or "you searched for" in low:
            continue
        items.append({"title": title, "link": link, "source": source_name, "time": "Recent"})
        if len(items) >= 15:
            break
    print(f"Found {len(items)} items")
    for i, it in enumerate(items[:5]):
        print(f"  {i+1}. {it['title']}")
except Exception as e:
    print(f"RSS FETCH ERROR: {e}")
    traceback.print_exc()
    items = []

# ── Step 2: Run semantic analysis ──
print("\n" + "=" * 60)
print("Step 2: Semantic analysis")
try:
    verification = _semantic_verify_claim(query, items)
    print(f"  verified: {verification['verified']}")
    print(f"  confidence: {verification['confidence']}")
    print(f"  reason: {verification['reason']}")
except Exception as e:
    print(f"SEMANTIC ERROR: {e}")
    traceback.print_exc()

# ── Step 3: Format the reply ──
print("\n" + "=" * 60)
print("Step 3: Format reply")
try:
    display_q = search_q if len(search_q) <= 200 else search_q[:197] + "..."

    lines = []
    for i, it in enumerate(items[:10], 1):
        src = f" \u2014 {it['source']}" if it.get("source") else ""
        link = it.get("link") or ""
        link_str = f" [Article]({link})" if link else ""
        lines.append(f"{i}. {it['title']}{src}{link_str}")
    block = "\n".join(lines)

    if verification["verified"]:
        status_para = (
            "\n\n**STATUS: \u2705 Verified News**\n"
            f"Semantic analysis confirms: {verification['reason']} "
            f"(Confidence: {verification['confidence']})"
        )
    elif verification["confidence"] == "high" and not verification["verified"]:
        status_para = (
            "\n\n**STATUS: \u26a0\ufe0f Likely False / Misleading**\n"
            f"Semantic analysis: {verification['reason']} "
            "Headlines mention the same people/topics but describe a DIFFERENT event. "
            "Disclaimer: There is still a chance we are wrong."
        )
    else:
        status_para = (
            "\n\n**STATUS: \u2753 Unverified**\n"
            f"Semantic analysis: {verification['reason']} "
            "The headlines found don't clearly confirm your specific claim. "
            "Try searching on X.com for more info."
        )

    status_para_clean = status_para.strip()
    reply = (
        f"{status_para_clean}\n\n"
        f"Found {len(items)} headline(s).\n\n{block}"
    )
    print("SUCCESS: Reply generated")
    print(reply[:500])
except Exception as e:
    print(f"FORMAT ERROR: {e}")
    traceback.print_exc()

print("\n\nDONE")
