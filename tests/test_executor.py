from __future__ import annotations

from core.executor import ExecutionPlan, execute_route


def test_execute_route_code() -> None:
    plan = execute_route("code", "fix my bug")
    assert isinstance(plan, ExecutionPlan)
    assert plan.action == "llm_code"
    assert plan.route == "code"
    assert len(plan.next_steps) > 0


def test_execute_route_unknown_defaults_to_general() -> None:
    plan = execute_route("unknown_route", "some input")
    assert plan.action == "llm_general"


def test_execute_route_all_known() -> None:
    for route in ("code", "research", "general"):
        plan = execute_route(route, "input")
        assert plan.route == route
        assert plan.action.startswith("llm_")

    # ops route now dispatches to real tools based on input content
    ops_shell = execute_route("ops", "ls /tmp")
    assert ops_shell.action == "run_shell"

    ops_http = execute_route("ops", "https://example.com")
    assert ops_http.action == "http_fetch"
