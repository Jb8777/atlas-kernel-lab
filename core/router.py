from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from core.config_loader import load_json_config
from core.logger import get_logger

log = get_logger(__name__)


@dataclass(frozen=True)
class RouteResult:
    """
    Routing output for both API and CLI.
    """

    input: str
    route: str
    rationale: str
    timestamp_utc: str


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def route_text(text: str) -> RouteResult:
    """
    Simple heuristic router.

    Routes:
    - code
    - research
    - ops
    - general
    """
    cleaned = (text or "").strip()
    if not cleaned:
        raise ValueError("text must be a non-empty string")

    lowered = cleaned.lower()

    # Defaults (also optionally augmented by config below)
    code_keywords = ["bug", "debug", "python", "fastapi", "api", "function", "class", "refactor", "pytest", "unit test"]
    research_keywords = ["research", "summarize", "compare", "paper", "sources", "citations", "explain"]
    ops_keywords = ["deploy", "kubernetes", "docker", "incident", "on-call", "monitoring", "alert", "latency", "uptime"]

    # Optionally merge config-provided keywords if present
    cfg = load_json_config()
    try:
        routing_cfg = cfg.get("routing", {}) if isinstance(cfg, dict) else {}
        if isinstance(routing_cfg, dict):
            if isinstance(routing_cfg.get("code_keywords"), list):
                code_keywords.extend([str(x).lower() for x in routing_cfg["code_keywords"]])
            if isinstance(routing_cfg.get("research_keywords"), list):
                research_keywords.extend([str(x).lower() for x in routing_cfg["research_keywords"]])
            if isinstance(routing_cfg.get("ops_keywords"), list):
                ops_keywords.extend([str(x).lower() for x in routing_cfg["ops_keywords"]])
    except Exception:
        # Never allow config issues to break routing
        log.exception("failed to merge routing keywords from config")

    def any_hit(keywords: list[str]) -> bool:
        return any(k in lowered for k in keywords if k)

    # Fast-path: URL detection → http_fetch via ops route
    if "http" in lowered or "www" in lowered:
        return RouteResult(
            input=cleaned,
            route="ops",
            rationale="Detected URL → HTTP fetch",
            timestamp_utc=_utc_now_iso(),
        )

    # Fast-path: shell command execution
    if "run" in lowered or "execute" in lowered or "ls" in lowered:
        return RouteResult(
            input=cleaned,
            route="ops",
            rationale="Detected command execution",
            timestamp_utc=_utc_now_iso(),
        )

    if any_hit(code_keywords):
        route = "code"
        rationale = "Detected software engineering keywords."
    elif any_hit(research_keywords):
        route = "research"
        rationale = "Detected research/synthesis keywords."
    elif any_hit(ops_keywords):
        route = "ops"
        rationale = "Detected operations/infrastructure keywords."
    else:
        route = "general"
        rationale = "No specialized keywords detected; defaulted to general."

    result = RouteResult(
        input=cleaned,
        route=route,
        rationale=rationale,
        timestamp_utc=_utc_now_iso(),
    )

    log.debug("route result: %s", asdict(result))
    return result
