"""
semantic_router.py - Query intent classification with RBAC intersection
"""
from __future__ import annotations
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import RBAC_MATRIX

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Route Definitions with 10+ utterances each
# ─────────────────────────────────────────────

ROUTE_DEFINITIONS = {
    "finance_route": {
        "collections": ["finance"],
        "utterances": [
            "What is our total revenue for Q3?",
            "Show me the budget allocations for this year",
            "What are the financial projections for next quarter?",
            "How much did we spend on vendor payments?",
            "What is the operating margin?",
            "Give me the annual financial report",
            "What are the investor metrics?",
            "How much cash do we have on hand?",
            "What is the EBITDA?",
            "Show me the profit and loss statement",
            "What are the departmental budget breakdowns?",
            "What is the company valuation?",
            "How much was allocated to marketing spend?",
            "What are the quarterly earnings?",
            "Tell me about our debt obligations",
            "What is the return on equity?",
            "Show me the balance sheet",
            "What were the capital expenditures last year?",
        ],
    },
    "engineering_route": {
        "collections": ["engineering"],
        "utterances": [
            "How does the authentication service work?",
            "What happened during the last system incident?",
            "How do I set up the development environment?",
            "What is the API rate limiting policy?",
            "How do I onboard as a new engineer?",
            "What are the system SLA requirements?",
            "How do I access the production database?",
            "Explain the microservices architecture",
            "What is the deployment process?",
            "How do I debug a failing service?",
            "What are the sprint velocity metrics?",
            "What monitoring tools do we use?",
            "How do we handle service outages?",
            "What is the code review process?",
            "How do I set up the CI/CD pipeline?",
            "What are the infrastructure components?",
            "How does load balancing work in our system?",
            "What are the runbooks for incident response?",
        ],
    },
    "marketing_route": {
        "collections": ["marketing"],
        "utterances": [
            "How did the Q3 marketing campaign perform?",
            "What is our customer acquisition cost?",
            "What are our brand guidelines?",
            "How many leads did we generate last quarter?",
            "What is our market share?",
            "How did the email campaign perform?",
            "What is the conversion rate for paid ads?",
            "Who are our main competitors?",
            "What channels drive the most revenue?",
            "What is the ROI on our marketing spend?",
            "How do we position our product against competitors?",
            "What is the NPS score?",
            "Tell me about the annual marketing report",
            "What are the top customer acquisition channels?",
            "How much did we spend on digital advertising?",
            "What is the churn rate for customers?",
            "Tell me about brand awareness metrics",
            "What were the Q1 campaign results?",
        ],
    },
    "hr_general_route": {
        "collections": ["general", "hr"],
        "utterances": [
            "What is the leave policy?",
            "How many vacation days do I get?",
            "What is the code of conduct?",
            "How do I apply for a promotion?",
            "What are the employee benefits?",
            "What is the work from home policy?",
            "How do I submit a performance review?",
            "What is the expense reimbursement process?",
            "What is the onboarding process for new employees?",
            "What are the company values?",
            "How do I report a harassment incident?",
            "What is the salary review process?",
            "What health insurance options are available?",
            "How do I access the employee handbook?",
            "What are the guidelines for business travel?",
            "How do I take maternity or paternity leave?",
            "What is the performance improvement process?",
            "What are the working hours policy?",
        ],
    },
    "cross_department_route": {
        "collections": [],  # Will be filled with all accessible collections at query time
        "utterances": [
            "Give me a summary of everything happening at the company",
            "What are the key metrics across all departments?",
            "Tell me about the overall business performance",
            "What major decisions were made this quarter?",
            "How is the company doing overall?",
            "What are the priorities for next year across teams?",
            "What are the company-wide initiatives?",
            "Tell me about the strategic direction",
            "What are the biggest risks facing the company?",
            "Give me an executive summary",
            "What are the cross-functional projects?",
            "What is the overall headcount?",
            "Tell me everything you know",
            "What is new at FinSolve?",
            "Give me a briefing on all departments",
            "What are the OKRs for this year?",
        ],
    },
}

# Route to collection mapping
ROUTE_COLLECTIONS = {
    name: config["collections"]
    for name, config in ROUTE_DEFINITIONS.items()
}


def _build_router():
    """Build the semantic router using the semantic-router library."""
    try:
        from semantic_router import Route
        from semantic_router.layer import RouteLayer
        from semantic_router.encoders import OpenAIEncoder
        import os

        routes = [
            Route(
                name=name,
                utterances=config["utterances"],
            )
            for name, config in ROUTE_DEFINITIONS.items()
        ]

        encoder = OpenAIEncoder()
        layer = RouteLayer(encoder=encoder, routes=routes)
        return layer
    except Exception as e:
        logger.warning(f"Could not build semantic router: {e}. Falling back to keyword router.")
        return None


# ─────────────────────────────────────────────
# Keyword-based fallback router
# ─────────────────────────────────────────────

KEYWORD_MAP = {
    "finance_route": [
        "revenue", "budget", "financial", "profit", "loss", "earnings", "cash",
        "ebitda", "margin", "investment", "investor", "quarterly", "annual report",
        "balance sheet", "expenditure", "fiscal", "cost", "spend", "payment",
        "vendor payment", "allocation", "valuation",
    ],
    "engineering_route": [
        "api", "system", "architecture", "deployment", "database", "server",
        "incident", "bug", "code", "developer", "engineering", "onboard",
        "microservice", "infrastructure", "devops", "pipeline", "ci/cd",
        "sprint", "velocity", "sla", "runbook", "monitoring", "outage",
    ],
    "marketing_route": [
        "campaign", "marketing", "brand", "customer acquisition", "lead",
        "conversion", "roi", "competitor", "market share", "advertising",
        "digital marketing", "email campaign", "nps", "churn", "retention",
        "promotion", "channel", "cac",
    ],
    "hr_general_route": [
        "leave", "vacation", "policy", "benefit", "handbook", "conduct",
        "employee", "hr", "salary", "review", "performance", "onboarding",
        "work from home", "remote", "expense", "reimbursement", "health insurance",
        "maternity", "paternity", "harassment",
    ],
}


def _keyword_classify(query: str) -> str:
    """Simple keyword-based route classification fallback."""
    query_lower = query.lower()
    scores = {route: 0 for route in KEYWORD_MAP}

    for route, keywords in KEYWORD_MAP.items():
        for keyword in keywords:
            if keyword in query_lower:
                scores[route] += 1

    best_route = max(scores, key=scores.get)
    if scores[best_route] == 0:
        return "cross_department_route"
    return best_route


# Module-level router (lazy init)
_router = None


def _get_router():
    global _router
    if _router is None:
        _router = _build_router()
    return _router


def classify_query(query: str, user_role: str) -> dict:
    """
    Classify a query into a route and intersect with user's accessible collections.

    Returns:
        {
            "route": str,
            "target_collections": list[str],
            "access_denied": bool,
            "denied_reason": str | None,
        }
    """
    # Classify the route
    route_name = None
    router = _get_router()

    if router is not None:
        try:
            result = router(query)
            route_name = result.name if result else None
        except Exception as e:
            logger.warning(f"Semantic router failed: {e}")

    if route_name is None:
        # Fall back to keyword matching
        route_name = _keyword_classify(query)
        logger.info(f"Using keyword router: {route_name}")
    else:
        logger.info(f"Semantic router classified as: {route_name}")

    # Get required collections for this route
    route_collections = ROUTE_COLLECTIONS.get(route_name, [])

    # Get user's accessible collections
    user_collections = RBAC_MATRIX.get(user_role, [])

    # Cross-department route: use all user's accessible collections
    if route_name == "cross_department_route" or not route_collections:
        target_collections = user_collections
        return {
            "route": route_name,
            "target_collections": target_collections,
            "access_denied": False,
            "denied_reason": None,
        }

    # Intersect route collections with user's accessible collections
    accessible = [c for c in route_collections if c in user_collections]

    if not accessible:
        # User does not have access to the required collection
        dept_name = route_name.replace("_route", "").replace("_", " ").title()
        denied_reason = (
            f"You don't have access to {dept_name} documents. "
            f"Your role '{user_role}' can only access: {', '.join(user_collections)}."
        )
        return {
            "route": route_name,
            "target_collections": [],
            "access_denied": True,
            "denied_reason": denied_reason,
        }

    return {
        "route": route_name,
        "target_collections": accessible,
        "access_denied": False,
        "denied_reason": None,
    }

