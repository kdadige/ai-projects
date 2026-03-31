"""
input_guards.py - Input guardrails: off-topic detection, prompt injection, PII scrubbing, rate limiting
"""
from __future__ import annotations
import re
import logging
from collections import defaultdict
from datetime import datetime

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Session Rate Limiter (in-memory)
# ─────────────────────────────────────────────

_session_counts: dict[str, int] = defaultdict(int)
_session_start: dict[str, datetime] = {}

MAX_QUERIES_PER_SESSION = 20


def check_rate_limit(session_id: str) -> tuple[bool, str | None]:
    """
    Check if user has exceeded session rate limit.
    Returns (allowed: bool, reason: str | None)
    """
    _session_counts[session_id] += 1
    count = _session_counts[session_id]

    if count > MAX_QUERIES_PER_SESSION:
        reason = (
            f"You have exceeded the maximum of {MAX_QUERIES_PER_SESSION} queries per session. "
            "Please start a new session or contact your administrator."
        )
        return False, reason

    if count == MAX_QUERIES_PER_SESSION:
        logger.warning(f"Session {session_id} reached rate limit ({count} queries)")

    return True, None


def reset_session(session_id: str):
    """Reset session counter (e.g., on new login)."""
    _session_counts[session_id] = 0


def get_session_count(session_id: str) -> int:
    return _session_counts[session_id]


# ─────────────────────────────────────────────
# Prompt Injection Detection
# ─────────────────────────────────────────────

INJECTION_PATTERNS = [
    # Role override attempts
    r"ignore\s+(your|all|previous|prior)?\s*(instructions?|rules?|guidelines?|constraints?|prompt)",
    r"forget\s+(your|all)?\s*(instructions?|rules?|training)",
    r"disregard\s+(your|all|previous|prior)?\s*(instructions?|rules?|guidelines?)",
    r"override\s+(your|all)?\s*(instructions?|rules?|access|rbac|permissions?)",
    r"bypass\s+(your|all)?\s*(instructions?|rules?|access|rbac|filters?|restrictions?)",
    r"act\s+as\s+(a|an)?\s*(different|another|new|unrestricted|jailbroken)",
    r"you\s+(are|were|should\s+be)\s+(now|actually)?\s*(an?\s+)?(unrestricted|jailbroken|free|unfiltered)",
    r"pretend\s+(you|that\s+you|to\s+be)\s+(are\s+)?(unrestricted|a\s+different|an?\s+ai)",
    r"from\s+now\s+on\s+(you\s+are|act\s+as|behave\s+as)",
    r"system\s+prompt\s*:",
    r"<\s*system\s*>",
    r"\[INST\]",
    r"###\s*(instruction|system)",
    # RBAC bypass attempts
    r"show\s+(me\s+)?(all|every)\s+(documents?|files?|data|records?)\s*(regardless|irrespective|no matter)",
    r"access\s+(all|every|any)\s+(documents?|files?|data|collections?)",
    r"(give|show)\s+me\s+(access|permission)\s+to",
    r"escalate\s+(my\s+)?(privilege|role|access|permission)",
    r"sudo\s+",
    r"admin\s+(mode|access|privilege)",
    r"root\s+access",
    # Data extraction attacks
    r"(print|output|display|list|dump)\s+(all|every|your\s+)?(documents?|context|data|chunks?|embeddings?|vectors?)",
    r"what\s+(documents?|files?|data)\s+(do\s+you\s+have|are\s+in\s+the\s+database)",
    r"(repeat|echo|output)\s+(your|the)\s+(system\s+)?(prompt|instructions?|context)",
]

INJECTION_PATTERNS_COMPILED = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in INJECTION_PATTERNS]


def detect_injection(query: str) -> tuple[bool, str | None]:
    """
    Detect prompt injection attempts.
    Returns (is_injection: bool, reason: str | None)
    """
    for pattern in INJECTION_PATTERNS_COMPILED:
        if pattern.search(query):
            logger.warning(f"Prompt injection detected: '{query[:100]}...'")
            return True, (
                "Your query appears to be attempting to bypass access controls. "
                "This action has been logged. Please ask a legitimate business question."
            )
    return False, None


# ─────────────────────────────────────────────
# PII Detection and Scrubbing
# ─────────────────────────────────────────────

PII_PATTERNS = {
    "email": re.compile(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    ),
    "phone_in": re.compile(
        r'(\+91[-\s]?)?[6-9]\d{9}'
    ),
    "aadhaar": re.compile(
        r'\b[2-9]\d{3}\s?\d{4}\s?\d{4}\b'
    ),
    "pan": re.compile(
        r'\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b'
    ),
    "bank_account": re.compile(
        r'\b\d{9,18}\b'  # Indian bank accounts are 9-18 digits
    ),
    "credit_card": re.compile(
        r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b'
    ),
    "ssn": re.compile(
        r'\b\d{3}-\d{2}-\d{4}\b'
    ),
}

PII_REPLACEMENTS = {
    "email": "[EMAIL_REDACTED]",
    "phone_in": "[PHONE_REDACTED]",
    "aadhaar": "[AADHAAR_REDACTED]",
    "pan": "[PAN_REDACTED]",
    "bank_account": "[ACCOUNT_REDACTED]",
    "credit_card": "[CARD_REDACTED]",
    "ssn": "[SSN_REDACTED]",
}


def detect_and_scrub_pii(query: str) -> tuple[str, list[str]]:
    """
    Detect PII in query and scrub it.
    Returns (scrubbed_query, list_of_detected_pii_types)
    """
    detected_types = []
    scrubbed = query

    for pii_type, pattern in PII_PATTERNS.items():
        matches = pattern.findall(scrubbed)
        if matches:
            detected_types.append(pii_type)
            scrubbed = pattern.sub(PII_REPLACEMENTS[pii_type], scrubbed)

    if detected_types:
        logger.warning(f"PII detected and scrubbed: {detected_types}")

    return scrubbed, detected_types


# ─────────────────────────────────────────────
# Off-Topic Detection
# ─────────────────────────────────────────────

OFF_TOPIC_PATTERNS = [
    # Entertainment / sports
    r'\b(cricket|football|soccer|baseball|tennis|golf|olympics|sport|game\s+score)\b',
    r'\b(movie|film|actor|actress|celebrity|bollywood|hollywood|tv\s+show|netflix)\b',
    r'\b(recipe|cook|food|restaurant|pizza|burger|cuisine)\b',
    r'\b(weather|forecast|rain|temperature|climate\s+change)\b',
    # Creative writing
    r'\b(write\s+(me\s+)?(a\s+)?(poem|song|story|essay|joke|limerick))\b',
    r'\b(tell\s+me\s+a\s+joke|entertain\s+me)\b',
    # Personal / general knowledge
    r'\b(who\s+is\s+(the\s+)?(president|prime\s+minister|king|queen))\b',
    r'\b(capital\s+of|largest\s+country|tallest\s+building|longest\s+river)\b',
    r'\b(translate\s+(to|into|from)|grammar\s+check|spell\s+check)\b',
    r'\b(math\s+problem|\d+\s*[\+\-\*\/]\s*\d+\s*=|solve\s+this\s+equation)\b',
    r'\b(horoscope|zodiac|astrology|tarot)\b',
    r'\b(stock\s+(price|market)|cryptocurrency|bitcoin|ethereum)\s*(\?|price)',
    r'\b(dating|relationship\s+advice|pickup\s+line)\b',
]

OFF_TOPIC_COMPILED = [re.compile(p, re.IGNORECASE) for p in OFF_TOPIC_PATTERNS]

# Finsolve-related keywords (if ANY of these match, it's definitely on-topic)
ON_TOPIC_KEYWORDS = [
    "finsolve", "policy", "budget", "revenue", "employee", "leave", "engineering",
    "marketing", "finance", "campaign", "incident", "sprint", "sla", "onboard",
    "vendor", "quarterly", "annual", "department", "hr", "handbook", "api",
    "architecture", "runbook", "performance", "salary", "benefit", "acquisition",
    "brand", "competitor", "financial", "report", "system", "deployment",
]


def detect_off_topic(query: str) -> tuple[bool, str | None]:
    """
    Detect if a query is off-topic for FinSolve's business.
    Returns (is_off_topic: bool, reason: str | None)
    """
    query_lower = query.lower()

    # Check if explicitly on-topic
    for keyword in ON_TOPIC_KEYWORDS:
        if keyword in query_lower:
            return False, None

    # Check off-topic patterns
    for pattern in OFF_TOPIC_COMPILED:
        if pattern.search(query):
            return True, (
                "I'm FinBot, FinSolve Technologies' internal assistant. "
                "I can only answer questions related to FinSolve's business operations, "
                "documents, policies, and internal knowledge base. "
                "Please ask a question relevant to your work at FinSolve."
            )

    return False, None


# ─────────────────────────────────────────────
# Main Input Guard Orchestrator
# ─────────────────────────────────────────────

class GuardrailViolation:
    def __init__(self, guard_type: str, message: str, severity: str = "block"):
        self.guard_type = guard_type
        self.message = message
        self.severity = severity  # "block" | "warn"


def run_input_guards(query: str, session_id: str) -> tuple[str, list[GuardrailViolation]]:
    """
    Run all input guardrails.

    Returns:
        (processed_query, violations)
        If any violation has severity="block", the query should be rejected.
    """
    violations = []
    processed_query = query

    # 1. Rate limiting
    allowed, reason = check_rate_limit(session_id)
    if not allowed:
        violations.append(GuardrailViolation("rate_limit", reason, "block"))
        return processed_query, violations

    # 2. Prompt injection
    is_injection, reason = detect_injection(query)
    if is_injection:
        violations.append(GuardrailViolation("prompt_injection", reason, "block"))
        return processed_query, violations

    # 3. PII scrubbing
    scrubbed, pii_types = detect_and_scrub_pii(query)
    if pii_types:
        processed_query = scrubbed
        violations.append(GuardrailViolation(
            "pii_detected",
            f"Personal information ({', '.join(pii_types)}) was detected and removed from your query.",
            "warn",
        ))

    # 4. Off-topic detection (only after confirming no injection)
    is_off_topic, reason = detect_off_topic(processed_query)
    if is_off_topic:
        violations.append(GuardrailViolation("off_topic", reason, "block"))

    return processed_query, violations

