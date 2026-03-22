from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any

from core.llm_client import LLMClientError, call_llm
from core.logger import get_logger
from tools.http import run_http_request
from tools.shell import run_shell_command

log = get_logger(__name__)


MODEL_BY_ACTION: dict[str, str] = {
    "llm_code": "deepseek-coder:6.7b",
    "llm_ops": "deepseek-coder:6.7b",
    "llm_research": "mistral",
    "llm_general": "mistral",
}


ROUTE_SYSTEM_PROMPTS: dict[str, str] = {
    "code": (
        "You are a senior software engineer. Produce working code or direct fixes immediately. "
        "Do NOT ask for more information. If context is missing, assume a reasonable example and proceed."
    ),
    "research": (
        "You are a research analyst. Provide structured, detailed answers with comparisons and insights. "
        "Avoid generic summaries."
    ),
    "ops": (
        "You are a senior SRE. Provide commands, diagnostics, and remediation steps. "
        "Focus on execution, not theory."
    ),
    "general": (
        "Provide clear, useful answers directly. Do not ask unnecessary questions."
    ),
}

ROUTE_ACTIONS: dict[str, str] = {
    "code": "llm_code",
    "research": "llm_research",
    "ops": "llm_ops",
    "general": "llm_general",
}


@dataclass
class ExecutionPlan:
    """
    Describes what will be run for a given route.
    """

    route: str
    action: str
    next_steps: list[str]


def execute_route(route: str, input_text: str) -> ExecutionPlan:
    """
    Build an execution plan for the given route.

    Does not perform any I/O — safe to call in tests.
    """
    lowered = input_text.lower()
    if route == "ops":
        action = "http_fetch" if ("http" in lowered or "www" in lowered) else "run_shell"
    else:
        action = ROUTE_ACTIONS.get(route, "llm_general")

    next_steps = [
        f"Execute {action} with provided input",
        "Return structured result to caller",
    ]

    return ExecutionPlan(route=route, action=action, next_steps=next_steps)


def _clean_step(raw: str) -> str:
    """Strip whitespace and remove leading run/fetch prefixes from a single step."""
    s = raw.strip()
    if s.startswith("run "):
        s = s.replace("run ", "", 1)
    if s.startswith("fetch "):
        s = s.replace("fetch ", "", 1)
    return s


def _detect_action(step: str) -> str:
    """Detect the appropriate action for a cleaned step string.

    Priority order:
    1. LLM — explanation/analysis keywords
    2. HTTP — URL patterns
    3. Shell — default for ops-style input
    """
    lowered = step.lower()
    if any(k in lowered for k in ("explain", "what", "why", "analyze")):
        return "llm_general"
    if "http" in lowered or "www" in lowered:
        return "http_fetch"
    return "run_shell"


def _execute_step(step: str, action: str, context: dict[str, Any] | None = None) -> str:
    """Run a single cleaned step and return its output string."""
    if action.startswith("llm"):
        ctx = context or {}
        prompt = f"Context:\n{ctx}\n\nTask:\n{step}"
        chosen_model = MODEL_BY_ACTION.get(action)
        old_model = os.environ.get("OLLAMA_MODEL")
        try:
            if chosen_model:
                os.environ["OLLAMA_MODEL"] = chosen_model
            return call_llm(prompt)
        except LLMClientError as e:
            return f"ERROR: {e}"
        finally:
            if chosen_model:
                if old_model is None:
                    os.environ.pop("OLLAMA_MODEL", None)
                else:
                    os.environ["OLLAMA_MODEL"] = old_model
    if action == "http_fetch":
        return run_http_request(step)
    return run_shell_command(step)


def _evaluate_condition(condition: str, context: dict[str, Any]) -> bool:
    """Ask the LLM to evaluate a natural-language condition against current context."""
    prompt = (
        f"Evaluate condition:\n\nCondition:\n{condition}\n\n"
        f"Previous output:\n{context.get('last_output', '')}\n\n"
        "Return ONLY: true or false"
    )
    try:
        verdict = call_llm(prompt)
    except LLMClientError:
        verdict = "false"
    lowered = verdict.lower()
    return "true" in lowered and "false" not in lowered


def _expand_to_steps(input_text: str) -> str:
    """Use the LLM to decompose a task into 'then'-separated execution steps."""
    prompt = (
        "Break this task into execution steps joined by 'then'.\n"
        "Use only: allowed shell commands (ls, pwd, whoami, date, uname), "
        "URLs (http://...), or reasoning steps (explain/analyze/what/why).\n"
        "Return ONLY the steps. No explanations, no numbering.\n\n"
        f"Task: {input_text}"
    )
    try:
        return call_llm(prompt)
    except LLMClientError:
        return input_text


def _execute_loop(inner_cmd: str, n: int, context: dict[str, Any]) -> str:
    """Execute inner_cmd n times, storing each output. Returns joined results."""
    outputs = []
    for _ in range(n):
        action = _detect_action(inner_cmd)
        try:
            out = _execute_step(inner_cmd, action, context)
        except Exception as e:
            out = f"ERROR: {e}"
        outputs.append(out)
        context["last_output"] = out
    return "\n---\n".join(outputs)


def run_execution(plan: ExecutionPlan, input_text: str) -> dict[str, Any]:
    """
    Full agent execution engine.

    Supports: multi-step, if/else branching, loops, structured memory,
    context-aware LLM, task auto-planning, safety enforcement, error isolation.
    Single-step (no "then") falls through to the legacy tool/LLM path.
    """
    # TASK PLANNING — auto-expand when no explicit "then" steps
    expanded = input_text
    if "then" not in input_text:
        lowered = input_text.lower()
        needs_planning = any(k in lowered for k in ("analyze", "audit", "investigate", "review"))
        if needs_planning:
            try:
                expanded = _expand_to_steps(input_text)
                log.info("task planner expanded input to: %s", expanded)
            except Exception:
                expanded = input_text

    # MULTI-STEP ENGINE
    if "then" in expanded:
        raw_steps = expanded.split("then")

        context: dict[str, Any] = {"history": []}
        results: list[dict[str, Any]] = []
        skip_mode = False
        else_mode = False

        for i, raw in enumerate(raw_steps):
            step = _clean_step(raw)
            if not step:
                continue

            step_lower = step.lower()

            # ── LOOP ────────────────────────────────────────────────────────
            m = re.match(r"repeat\s+(\d+)\s+times?\s+(.*)", step_lower, re.IGNORECASE)
            if m:
                n = min(int(m.group(1)), 10)  # safety cap
                inner = _clean_step(m.group(2))
                try:
                    output = _execute_loop(inner, n, context)
                except Exception as e:
                    output = f"ERROR: {e}"
                context[f"step_{i}"] = output
                context["last_output"] = output
                context["history"].append(output)
                results.append({"step": step, "action": "loop", "output": output})
                continue

            # ── ELSE ─────────────────────────────────────────────────────────
            if step_lower.startswith("else"):
                skip_mode = not skip_mode
                else_mode = True
                results.append({"step": step, "action": "else", "output": f"else branch — skip_mode={skip_mode}"})
                continue

            # ── CONDITION ────────────────────────────────────────────────────
            if step_lower.startswith("if "):
                else_mode = False
                passed = _evaluate_condition(step, context)
                skip_mode = not passed
                results.append({
                    "step": step,
                    "action": "condition",
                    "output": "PASSED (condition true)" if passed else "SKIPPED (condition false)",
                })
                continue

            # ── SKIP ─────────────────────────────────────────────────────────
            if skip_mode:
                results.append({"step": step, "action": "skipped", "output": "SKIPPED (previous condition false)"})
                continue

            # ── EXECUTE ──────────────────────────────────────────────────────
            action = _detect_action(step)
            try:
                output = _execute_step(step, action, context)
            except Exception as e:
                output = f"ERROR: {e}"
                log.exception("step execution failed: %s", step)

            context[f"step_{i}"] = output
            context["last_output"] = output
            context["history"].append(output)
            results.append({"step": step, "action": action, "output": output})

        return {
            "status": "success",
            "steps": results,
            "context": context,
            "final_output": context.get("last_output"),
        }

    # ── SINGLE-STEP (legacy path) ─────────────────────────────────────────────
    cleaned_text = input_text.strip()

    if cleaned_text.startswith("run "):
        cleaned_text = cleaned_text.replace("run ", "", 1)

    if cleaned_text.startswith("fetch "):
        cleaned_text = cleaned_text.replace("fetch ", "", 1)

    if plan.action == "run_shell":
        return {
            "status": "success",
            "action": "run_shell",
            "output": run_shell_command(cleaned_text),
            "error": "",
        }

    if plan.action == "http_fetch":
        return {
            "status": "success",
            "action": "http_fetch",
            "output": run_http_request(cleaned_text),
            "error": "",
        }

    system_prompt = ROUTE_SYSTEM_PROMPTS.get(plan.route, ROUTE_SYSTEM_PROMPTS["general"])

    try:
        output = call_llm(input_text, system=system_prompt)
        return {"status": "success", "output": output, "action": plan.action}
    except LLMClientError as e:
        log.warning("LLM call failed for route %s: %s", plan.route, e)
        return {"status": "error", "output": str(e), "action": plan.action}
