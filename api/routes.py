from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.executor import ExecutionPlan, execute_route, run_execution
from core.logger import get_logger
from core.router import RouteResult, route_text

router = APIRouter()
log = get_logger(__name__)


class RouteRequest(BaseModel):
    """
    Request payload for /route.
    """

    text: str = Field(..., min_length=1, description="Task/prompt text to route and execute.")


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
        routing = route_text(payload.text)
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
