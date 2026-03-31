"""
test_routing.py - Tests for semantic query routing
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestSemanticRouter:

    def test_finance_query_routes_for_finance_user(self):
        from routing.semantic_router import classify_query
        result = classify_query("What is the Q3 revenue?", "finance")
        assert result["access_denied"] is False
        assert "finance" in result["target_collections"]

    def test_hr_query_routes_for_employee(self):
        from routing.semantic_router import classify_query
        result = classify_query("What is the leave policy?", "employee")
        assert result["access_denied"] is False
        assert "general" in result["target_collections"]

    def test_engineering_query_routes_for_engineering_user(self):
        from routing.semantic_router import classify_query
        result = classify_query("How do I set up the development environment?", "engineering")
        assert result["access_denied"] is False
        assert "engineering" in result["target_collections"]

    def test_marketing_query_routes_for_marketing_user(self):
        from routing.semantic_router import classify_query
        result = classify_query("How did the Q3 campaign perform?", "marketing")
        assert result["access_denied"] is False
        assert "marketing" in result["target_collections"]

    def test_cross_dept_route_for_c_level(self):
        from routing.semantic_router import classify_query
        from config import RBAC_MATRIX
        result = classify_query("Give me a summary of everything", "c_level")
        assert result["access_denied"] is False
        c_level_collections = RBAC_MATRIX["c_level"]
        for col in result["target_collections"]:
            assert col in c_level_collections

    def test_route_names_are_valid(self):
        from routing.semantic_router import ROUTE_DEFINITIONS
        valid_routes = {
            "finance_route", "engineering_route", "marketing_route",
            "hr_general_route", "cross_department_route"
        }
        for route_name in ROUTE_DEFINITIONS:
            assert route_name in valid_routes

    def test_each_route_has_10_utterances(self):
        from routing.semantic_router import ROUTE_DEFINITIONS
        for route_name, config in ROUTE_DEFINITIONS.items():
            utterances = config["utterances"]
            assert len(utterances) >= 10, (
                f"Route '{route_name}' only has {len(utterances)} utterances, need at least 10"
            )

    def test_keyword_fallback_finance(self):
        from routing.semantic_router import _keyword_classify
        route = _keyword_classify("Show me the revenue and budget for Q3")
        assert route == "finance_route"

    def test_keyword_fallback_engineering(self):
        from routing.semantic_router import _keyword_classify
        route = _keyword_classify("There was a system outage and incident yesterday")
        assert route == "engineering_route"

    def test_keyword_fallback_marketing(self):
        from routing.semantic_router import _keyword_classify
        route = _keyword_classify("How did our marketing campaign convert customers?")
        assert route == "marketing_route"

    def test_keyword_fallback_hr(self):
        from routing.semantic_router import _keyword_classify
        route = _keyword_classify("What is the leave policy and employee benefit?")
        assert route == "hr_general_route"

    def test_finance_route_blocked_for_employee(self):
        from routing.semantic_router import classify_query
        result = classify_query("What is the Q3 revenue?", "employee")
        assert result["access_denied"] is True or "finance" not in result["target_collections"]

    def test_engineering_route_blocked_for_marketing_user(self):
        from routing.semantic_router import classify_query
        result = classify_query("How do I set up the development environment?", "marketing")
        assert result["access_denied"] is True or "engineering" not in result["target_collections"]

