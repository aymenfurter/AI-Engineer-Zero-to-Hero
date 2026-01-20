"""
Observability Lab Package

This package provides utilities for adding tracing and monitoring to AI agents and workflows.

Quick Start:
    from observability import setup_tracing, with_agent_telemetry
    
    # Initialize tracing (call once at startup)
    setup_tracing(service_name="my-agent")
    
    # Decorate agent functions
    @with_agent_telemetry("MyAgent")
    async def call_agent(prompt: str) -> str:
        ...

Modules:
    - tracing: OpenTelemetry setup and configuration
    - maf_wrapper: Agent telemetry decorators and workflow tracer
    - debug_events: Event emission for real-time monitoring
"""

from .tracing import (
    setup_tracing,
    is_tracing_enabled,
    get_trace_count,
    reset_trace_count,
    get_tracer,
    trace_agent_call,
)

from .maf_wrapper import (
    with_agent_telemetry,
    WorkflowTracer,
    sse_event,
    sse_status,
    sse_error,
    sse_done,
)

from .debug_events import (
    DebugEventEmitter,
    create_debug_emitter,
)

__all__ = [
    # Tracing setup
    "setup_tracing",
    "is_tracing_enabled",
    "get_trace_count",
    "reset_trace_count",
    "get_tracer",
    "trace_agent_call",
    # Agent telemetry
    "with_agent_telemetry",
    "WorkflowTracer",
    # SSE utilities
    "sse_event",
    "sse_status",
    "sse_error",
    "sse_done",
    # Debug events
    "DebugEventEmitter",
    "create_debug_emitter",
]
