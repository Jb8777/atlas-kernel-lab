from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.executor import ExecutionPlan, execute_route, run_execution
from core.logger import get_logger
from core.router import RouteResult, route_text

router = APIRouter()
log = get_logger(__name__)


def build_effective_input(payload: "RouteRequest") -> str:
    """
    Convert legacy or structured request bodies into one effective execution string.
    """
    if payload.text and payload.text.strip():
        return payload.text.strip()

    parts: list[str] = []

    if payload.task:
        parts.append(f"Task: {payload.task.strip()}")
    if payload.code:
        parts.append("Code:\n```python\n" + payload.code.strip() + "\n```")
    if payload.error:
        parts.append(f"Error: {payload.error.strip()}")
    if payload.goal:
        parts.append(f"Goal: {payload.goal.strip()}")

    effective = "\n\n".join(parts).strip()
    if not effective:
        raise ValueError("Provide either 'text' or at least one structured field: task, code, error, goal")

    return effective



class RouteRequest(BaseModel):
    """
    Request payload for /route.

    Supports either:
    - text: legacy flat prompt
    - structured fields: task/code/error/goal
    """

    text: str | None = Field(default=None, min_length=1, description="Legacy flat task/prompt text.")
    task: str | None = Field(default=None, min_length=1, description="High-level task, e.g. fix bug.")
    code: str | None = Field(default=None, min_length=1, description="Relevant source code.")
    error: str | None = Field(default=None, min_length=1, description="Observed error message or failure mode.")
    goal: str | None = Field(default=None, min_length=1, description="Desired outcome.")


class HealthResponse(BaseModel):
    status: str
    service: str
    env: str


class RouteResponse(BaseModel):
    """
    /route response includes:
    - routing result (classification)
    - execution plan (action + next steps)
    - execution result (real output from LLM/tools)
    """

    routing: RouteResult
    execution: ExecutionPlan
    result: dict


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """
    Basic service health check.
    """
    from core.config_loader import get_settings  # avoid early env/config side effects at import time

    settings = get_settings()
    return HealthResponse(status="ok", service=settings.app_name, env=settings.app_env)


@router.post("/route", response_model=RouteResponse)
def route_endpoint(payload: RouteRequest) -> RouteResponse:
    """
    Route a prompt, create an execution plan, then execute it.
    """
    try:
        effective_input = build_effective_input(payload)
        routing = route_text(effective_input)
        execution = execute_route(routing.route, routing.input)
        result = run_execution(execution, routing.input)

        log.info(
            "route executed",
            extra={"route": routing.route, "action": execution.action, "status": result.get("status")},
        )

        return RouteResponse(routing=routing, execution=execution, result=result)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        log.exception("route/execute failed")
        raise HTTPException(status_code=500, detail="Internal routing/execution error") from e
