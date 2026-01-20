"""
Microsoft Agent Framework (MAF) Wrapper for Enhanced Observability.

This module provides utilities to wrap agent calls with:
- OpenTelemetry spans for distributed tracing
- Usage metrics capture
- Structured logging
- Debug event emission

Based on patterns from production AI applications.
"""

import functools
import json
import logging
import time
from typing import Any, Callable, TypeVar, Optional

logger = logging.getLogger(__name__)

T = TypeVar("T")


# =============================================================================
# Agent Instrumentation Decorator
# =============================================================================

def with_agent_telemetry(
    agent_name: str,
    description: str = "Agent call",
    capture_input: bool = True,
    capture_output: bool = True
):
    """
    Decorator that adds comprehensive telemetry to any async agent function.
    
    This wraps the decorated function with:
    - OpenTelemetry span for distributed tracing
    - Timing metrics
    - Input/output capture (optional, for debugging)
    - Error tracking
    
    Example:
        @with_agent_telemetry("PlannerAgent", "Generate presentation outline")
        async def generate_outline(self, request: str) -> PresentationOutline:
            response = await self._agent.run(...)
            return response.value
    
    Args:
        agent_name: Name to identify this agent in traces
        description: Human-readable description of what the agent does
        capture_input: Whether to record input in trace attributes
        capture_output: Whether to record output in trace attributes
    """
    def decorator(fn: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs) -> T:
            from tracing import get_tracer, is_tracing_enabled
            from opentelemetry import trace as otel_trace
            
            tracer = get_tracer(f"agent.{agent_name}")
            start_time = time.time()
            
            # Create span for this agent call
            with tracer.start_as_current_span(
                f"{agent_name}.{fn.__name__}",
                kind=otel_trace.SpanKind.CLIENT,
                attributes={
                    "agent.name": agent_name,
                    "agent.description": description,
                    "gen_ai.system": "azure_foundry",
                }
            ) as span:
                try:
                    # Capture input if enabled
                    if capture_input and args:
                        # Try to capture meaningful input
                        input_str = _safe_serialize_args(args, kwargs)
                        if input_str and len(input_str) < 10000:
                            span.set_attribute("gen_ai.prompt", input_str)
                    
                    # Execute the actual function
                    result = await fn(*args, **kwargs)
                    
                    # Capture output if enabled
                    if capture_output and result is not None:
                        output_str = _safe_serialize_result(result)
                        if output_str and len(output_str) < 10000:
                            span.set_attribute("gen_ai.completion", output_str)
                    
                    # Record success
                    duration_ms = (time.time() - start_time) * 1000
                    span.set_attribute("agent.duration_ms", duration_ms)
                    span.set_status(otel_trace.StatusCode.OK)
                    
                    logger.debug(
                        f"✅ {agent_name}.{fn.__name__} completed in {duration_ms:.0f}ms"
                    )
                    
                    return result
                    
                except Exception as e:
                    # Record error
                    duration_ms = (time.time() - start_time) * 1000
                    span.set_attribute("agent.duration_ms", duration_ms)
                    span.set_status(otel_trace.StatusCode.ERROR, str(e))
                    span.record_exception(e)
                    
                    logger.error(
                        f"❌ {agent_name}.{fn.__name__} failed after {duration_ms:.0f}ms: {e}"
                    )
                    raise
        
        return wrapper
    return decorator


def _safe_serialize_args(args: tuple, kwargs: dict) -> str:
    """Safely serialize function arguments for tracing."""
    try:
        # Skip 'self' argument
        meaningful_args = args[1:] if args and hasattr(args[0], '__class__') else args
        
        parts = []
        for arg in meaningful_args:
            if isinstance(arg, str):
                parts.append(arg[:1000])
            elif hasattr(arg, 'model_dump'):
                parts.append(json.dumps(arg.model_dump())[:1000])
            elif isinstance(arg, (dict, list)):
                parts.append(json.dumps(arg)[:1000])
            else:
                parts.append(str(arg)[:500])
        
        for key, value in kwargs.items():
            if isinstance(value, str):
                parts.append(f"{key}={value[:500]}")
        
        return " | ".join(parts)
    except Exception:
        return ""


def _safe_serialize_result(result: Any) -> str:
    """Safely serialize function result for tracing."""
    try:
        if isinstance(result, str):
            return result[:5000]
        if hasattr(result, 'model_dump'):
            return json.dumps(result.model_dump())[:5000]
        if isinstance(result, dict):
            return json.dumps(result)[:5000]
        return str(result)[:2000]
    except Exception:
        return ""


# =============================================================================
# Workflow Tracing Utilities
# =============================================================================

class WorkflowTracer:
    """
    Context manager for tracing multi-step workflows.
    
    Usage:
        async with WorkflowTracer("slideshow_builder", total_steps=5) as wt:
            wt.start_step("planning", "Generate presentation outline")
            outline = await planner.generate_outline(request)
            wt.complete_step(success=True, details={"slides": len(outline.slides)})
            
            for i, slide in enumerate(outline.slides):
                wt.start_step(f"slide_{i}", f"Select image for {slide.subject}")
                ...
    """
    
    def __init__(
        self,
        workflow_name: str,
        total_steps: int = 0,
        event_callback: Optional[Callable[[dict], Any]] = None
    ):
        self.workflow_name = workflow_name
        self.total_steps = total_steps
        self.current_step = 0
        self.event_callback = event_callback
        self._start_time = None
        self._step_start_time = None
        self._span = None
        self._tracer = None
    
    async def __aenter__(self):
        from tracing import get_tracer
        from opentelemetry import trace as otel_trace
        
        self._tracer = get_tracer(f"workflow.{self.workflow_name}")
        self._start_time = time.time()
        
        # Start workflow span
        self._span = self._tracer.start_span(
            f"workflow.{self.workflow_name}",
            kind=otel_trace.SpanKind.INTERNAL,
            attributes={
                "workflow.name": self.workflow_name,
                "workflow.total_steps": self.total_steps,
            }
        )
        
        self._emit_event("workflow_started", {
            "workflow": self.workflow_name,
            "total_steps": self.total_steps,
        })
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        from opentelemetry import trace as otel_trace
        
        duration_ms = (time.time() - self._start_time) * 1000
        
        if exc_type is None:
            self._span.set_status(otel_trace.StatusCode.OK)
            self._emit_event("workflow_completed", {
                "workflow": self.workflow_name,
                "duration_ms": duration_ms,
                "steps_completed": self.current_step,
            })
        else:
            self._span.set_status(otel_trace.StatusCode.ERROR, str(exc_val))
            self._span.record_exception(exc_val)
            self._emit_event("workflow_error", {
                "workflow": self.workflow_name,
                "duration_ms": duration_ms,
                "error": str(exc_val),
            })
        
        self._span.set_attribute("workflow.duration_ms", duration_ms)
        self._span.set_attribute("workflow.steps_completed", self.current_step)
        self._span.end()
        
        return False  # Don't suppress exceptions
    
    def start_step(self, step_id: str, description: str, **attributes) -> None:
        """Start a new workflow step."""
        self.current_step += 1
        self._step_start_time = time.time()
        
        self._span.add_event(
            f"step.{step_id}.started",
            attributes={
                "step.id": step_id,
                "step.number": self.current_step,
                "step.description": description,
                **attributes,
            }
        )
        
        self._emit_event("step_started", {
            "step_id": step_id,
            "step_number": self.current_step,
            "total_steps": self.total_steps,
            "description": description,
            **attributes,
        })
    
    def complete_step(
        self,
        success: bool = True,
        details: Optional[dict] = None,
        error: Optional[str] = None
    ) -> None:
        """Complete the current workflow step."""
        duration_ms = (time.time() - self._step_start_time) * 1000 if self._step_start_time else 0
        
        event_attrs = {
            "step.number": self.current_step,
            "step.success": success,
            "step.duration_ms": duration_ms,
        }
        if details:
            for key, value in details.items():
                event_attrs[f"step.{key}"] = str(value)
        if error:
            event_attrs["step.error"] = error
        
        self._span.add_event(
            f"step.{self.current_step}.completed",
            attributes=event_attrs
        )
        
        self._emit_event("step_completed", {
            "step_number": self.current_step,
            "success": success,
            "duration_ms": duration_ms,
            "details": details,
            "error": error,
        })
    
    def _emit_event(self, event_type: str, data: dict) -> None:
        """Emit an event via the callback if configured."""
        if self.event_callback:
            self.event_callback({"type": event_type, **data})


# =============================================================================
# SSE Streaming Utilities
# =============================================================================

def sse_event(event_type: str, data: dict | str | None = None) -> str:
    """Format a Server-Sent Event."""
    if data is None:
        payload = {"type": event_type}
    elif isinstance(data, str):
        payload = {"type": event_type, "message": data}
    else:
        payload = {"type": event_type, **data}
    return f"data: {json.dumps(payload)}\n\n"


def sse_status(message: str) -> str:
    """Send a status update SSE."""
    return sse_event("status", message)


def sse_error(message: str) -> str:
    """Send an error SSE."""
    return sse_event("error", {"message": message})


def sse_done() -> str:
    """Send completion SSE."""
    return 'data: {"type": "done"}\n\n'
