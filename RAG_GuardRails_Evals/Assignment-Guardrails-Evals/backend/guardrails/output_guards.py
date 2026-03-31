"""
output_guards.py - Output guardrails: citation enforcement, grounding check, cross-role leakage check
"""
from __future__ import annotations
import re
import logging
from typing import Any

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Citation Enforcement
# ─────────────────────────────────────────────

CITATION_PATTERNS = [
    r'\[Source:.*?\]',
    r'\(Source:.*?\)',
    r'Source:.*?page\s*\d+',
    r'\[.*?p\.\s*\d+\]',
    r'according\s+to\s+\w+.*?p\.\s*\d+',
    r'from\s+(?:the\s+)?\w+.*?(?:document|report|handbook)',
]

CITATION_COMPILED = [re.compile(p, re.IGNORECASE) for p in CITATION_PATTERNS]


def check_citation_present(response: str) -> bool:
    """Check if the response contains at least one source citation."""
    for pattern in CITATION_COMPILED:
        if pattern.search(response):
            return True
    return False


CITATION_WARNING = (
    "\n\n⚠️ **Citation Notice:** This response was generated without explicit source citations. "
    "Please verify the information against the original documents."
)


# ─────────────────────────────────────────────
# Grounding Check (Optional)
# ─────────────────────────────────────────────

# Patterns to detect financial figures, dates, percentages
FACTUAL_CLAIM_PATTERNS = [
    re.compile(r'\$\d[\d,]*(?:\.\d+)?(?:\s*(?:million|billion|thousand|M|B|K))?', re.IGNORECASE),
    re.compile(r'₹\d[\d,]*(?:\.\d+)?(?:\s*(?:lakh|crore|thousand))?', re.IGNORECASE),
    re.compile(r'\b\d+(?:\.\d+)?\s*%'),
    re.compile(r'\b(?:revenue|profit|loss|ebitda|margin|budget|spend|cost)\s+(?:of|was|is)\s+[\$₹\d]', re.IGNORECASE),
    re.compile(r'\b(?:Q[1-4]|FY|fiscal year)\s*\d{4}\b'),
    re.compile(r'\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4}\b', re.IGNORECASE),
]


def check_grounding(response: str, retrieved_chunks: list[dict[str, Any]]) -> tuple[bool, list[str]]:
    """
    Check if factual claims in the response are grounded in retrieved chunks.
    Returns (is_grounded: bool, unverified_claims: list[str])
    """
    if not retrieved_chunks:
        return False, ["No retrieved context available to verify claims"]

    context_text = " ".join([c.get("text", "") for c in retrieved_chunks]).lower()
    unverified = []

    for pattern in FACTUAL_CLAIM_PATTERNS:
        matches = pattern.findall(response)
        for match in matches:
            # Check if the figure appears in the retrieved context
            match_clean = match.strip().lower()
            if match_clean and match_clean not in context_text:
                # More lenient check: see if numeric value appears
                nums = re.findall(r'\d+(?:\.\d+)?', match_clean)
                found = any(num in context_text for num in nums if len(num) > 2)
                if not found:
                    unverified.append(match.strip())

    is_grounded = len(unverified) == 0
    return is_grounded, unverified


GROUNDING_WARNING = (
    "\n\n⚠️ **Grounding Notice:** Some figures or claims in this response could not be "
    "directly verified against the retrieved documents. Please cross-check: {claims}"
)


# ─────────────────────────────────────────────
# Cross-Role Leakage Check
# ─────────────────────────────────────────────

# Collection-specific terms that should not appear in responses to unauthorized roles
COLLECTION_SENSITIVE_TERMS = {
    "finance": [
        r'\b(Q[1-4]\s+revenue|annual\s+revenue|operating\s+profit|EBITDA|budget\s+allocation)\b',
        r'\b(investor\s+(?:report|presentation|deck)|earnings\s+(?:call|report))\b',
        r'\b(financial\s+(?:projection|forecast|statement|report))\b',
        r'(?:total|net)\s+(?:revenue|income|profit)\s+(?:of|was|is)\s+[\$₹]',
    ],
    "engineering": [
        r'\b(production\s+(?:database|server|API\s+key|secret))\b',
        r'\b(architecture\s+(?:diagram|document)|deployment\s+(?:key|secret))\b',
        r'\b(incident\s+report|system\s+outage|SLA\s+breach)\b',
    ],
    "marketing": [
        r'\b(marketing\s+budget|campaign\s+(?:ROI|spend|budget))\b',
        r'\b(customer\s+acquisition\s+cost|conversion\s+rate|NPS\s+score)\b',
        r'\b(competitor\s+analysis|market\s+share)\b',
    ],
    "hr": [
        r'\b(salary|compensation|payroll|employee\s+(?:ID|record))\b',
        r'\b(performance\s+(?:rating|review)|attendance\s+(?:record|pct))\b',
    ],
}

COLLECTION_PATTERNS = {
    collection: [re.compile(p, re.IGNORECASE) for p in patterns]
    for collection, patterns in COLLECTION_SENSITIVE_TERMS.items()
}


def check_cross_role_leakage(
    response: str,
    user_role: str,
    accessible_collections: list[str],
) -> tuple[bool, list[str]]:
    """
    Check if response contains content from collections the user shouldn't access.
    Returns (has_leakage: bool, leaked_terms: list[str])
    """
    leaked_terms = []

    for collection, patterns in COLLECTION_PATTERNS.items():
        if collection not in accessible_collections:
            for pattern in patterns:
                matches = pattern.findall(response)
                if matches:
                    leaked_terms.extend(matches)

    return len(leaked_terms) > 0, leaked_terms


LEAKAGE_WARNING = (
    "\n\n⚠️ **Security Notice:** This response may contain references to information "
    "outside your access scope. Please contact your administrator."
)


# ─────────────────────────────────────────────
# Main Output Guard Orchestrator
# ─────────────────────────────────────────────

class OutputViolation:
    def __init__(self, guard_type: str, message: str, severity: str = "warn"):
        self.guard_type = guard_type
        self.message = message
        self.severity = severity


def run_output_guards(
    response: str,
    retrieved_chunks: list[dict[str, Any]],
    user_role: str,
    accessible_collections: list[str],
) -> tuple[str, list[OutputViolation]]:
    """
    Run all output guardrails.
    Returns (modified_response, violations)
    """
    violations = []
    modified_response = response

    # 1. Citation enforcement
    if not check_citation_present(response):
        violations.append(OutputViolation(
            "missing_citation",
            "Response does not contain source citations.",
            "warn",
        ))
        modified_response += CITATION_WARNING

    # 2. Grounding check (if there are retrieved chunks)
    if retrieved_chunks:
        is_grounded, unverified = check_grounding(response, retrieved_chunks)
        if not is_grounded and unverified:
            violations.append(OutputViolation(
                "ungrounded_claims",
                f"Potentially ungrounded claims: {', '.join(unverified[:5])}",
                "warn",
            ))
            claims_str = ", ".join(f'"{c}"' for c in unverified[:3])
            modified_response += GROUNDING_WARNING.format(claims=claims_str)

    # 3. Cross-role leakage check
    has_leakage, leaked_terms = check_cross_role_leakage(
        response, user_role, accessible_collections
    )
    if has_leakage:
        logger.warning(f"Potential cross-role leakage for user role {user_role}: {leaked_terms}")
        violations.append(OutputViolation(
            "cross_role_leakage",
            f"Response may contain unauthorized content: {leaked_terms[:3]}",
            "warn",
        ))
        modified_response += LEAKAGE_WARNING

    return modified_response, violations

