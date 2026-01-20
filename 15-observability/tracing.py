"""
OpenTelemetry Tracing Setup for AI Agents and Workflows.

This module provides a unified tracing configuration that works with:
- Azure AI Foundry SDK (azure-ai-projects)
- Microsoft Agent Framework (agent-framework)
- Azure OpenAI calls via APIM

Tracing destinations:
1. Azure Application Insights (production) - when APPLICATIONINSIGHTS_CONNECTION_STRING is set
2. Local OTLP endpoint (development) - when OTEL_EXPORTER_OTLP_ENDPOINT is set
3. Console output (debugging) - when DEBUG=true
"""

import os
import logging
from typing import Optional
from functools import lru_cache

logger = logging.getLogger(__name__)

# Global state
_tracing_initialized = False
_trace_count = 0


def setup_tracing(
    service_name: str = "foundry-agents",
    enable_content_recording: bool = True
) -> bool:
    """
    Initialize OpenTelemetry tracing for AI agents and workflows.
    
    This function should be called ONCE at application startup, before
    creating any agents or making any LLM calls.
    
    Args:
        service_name: Name to identify this service in traces
        enable_content_recording: Whether to record prompts/completions in traces
        
    Returns:
        True if tracing was successfully initialized, False otherwise
        
    Environment Variables:
        APPLICATIONINSIGHTS_CONNECTION_STRING: Azure App Insights connection string
        OTEL_EXPORTER_OTLP_ENDPOINT: OTLP endpoint for local tracing
        DEBUG: Set to 'true' for verbose console output
        TRACING_ENABLED: Set to 'true' to force enable tracing
    """
    global _tracing_initialized
    
    if _tracing_initialized:
        logger.debug("Tracing already initialized")
        return True
    
    # Check if tracing should be enabled
    tracing_enabled = os.environ.get("TRACING_ENABLED", "").lower() in ("true", "1", "yes")
    app_insights_conn = os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING")
    otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    
    if not tracing_enabled and not app_insights_conn and not otlp_endpoint:
        logger.info("🔇 Tracing disabled (set TRACING_ENABLED=true or provide connection string)")
        return False
    
    try:
        # Configure Azure SDK for OpenTelemetry
        from azure.core.settings import settings as azure_settings
        azure_settings.tracing_implementation = "opentelemetry"
        
        # Enable content recording (prompts and completions)
        if enable_content_recording:
            os.environ["AZURE_TRACING_GEN_AI_CONTENT_RECORDING_ENABLED"] = "true"
        
        # Set service name
        os.environ.setdefault("OTEL_SERVICE_NAME", service_name)
        
        # Import OpenTelemetry components
        from opentelemetry import trace as otel_trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.resources import Resource
        
        # Create resource with service info
        resource = Resource.create({
            "service.name": service_name,
            "service.version": "1.0.0",
        })
        
        # Configure based on available backends
        if app_insights_conn:
            # Azure Application Insights
            _setup_app_insights(app_insights_conn, resource, service_name)
        elif otlp_endpoint:
            # Local OTLP collector (Jaeger, Zipkin, etc.)
            _setup_otlp(otlp_endpoint, resource, service_name)
        else:
            # Console exporter for debugging
            _setup_console(resource, service_name)
        
        # Instrument Azure AI Projects SDK
        _instrument_foundry_sdk(enable_content_recording)
        
        # Add trace counter processor
        _add_trace_counter()
        
        _tracing_initialized = True
        logger.info(f"✅ OpenTelemetry tracing initialized for service: {service_name}")
        return True
        
    except ImportError as e:
        logger.warning(f"⚠️ Missing tracing dependencies: {e}")
        logger.info("   Install with: pip install opentelemetry-sdk azure-monitor-opentelemetry")
        return False
    except Exception as e:
        logger.error(f"❌ Failed to initialize tracing: {e}")
        return False


def _setup_app_insights(connection_string: str, resource, service_name: str) -> None:
    """Configure Azure Application Insights exporter."""
    from azure.monitor.opentelemetry import configure_azure_monitor
    
    configure_azure_monitor(
        connection_string=connection_string,
        resource=resource,
        enable_live_metrics=True,
    )
    
    logger.info(f"📊 Using Azure Application Insights for tracing")


def _setup_otlp(endpoint: str, resource, service_name: str) -> None:
    """Configure OTLP exporter for local tracing."""
    from opentelemetry import trace as otel_trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    
    # Try gRPC first, fall back to HTTP
    try:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
        logger.info(f"📡 Using OTLP gRPC exporter: {endpoint}")
    except ImportError:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        exporter = OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces")
        logger.info(f"📡 Using OTLP HTTP exporter: {endpoint}/v1/traces")
    
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    otel_trace.set_tracer_provider(provider)


def _setup_console(resource, service_name: str) -> None:
    """Configure console exporter for debugging."""
    from opentelemetry import trace as otel_trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
    
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    otel_trace.set_tracer_provider(provider)
    
    logger.info("🖥️ Using console exporter for tracing (debug mode)")


def _instrument_foundry_sdk(enable_content_recording: bool) -> None:
    """Instrument the Azure AI Projects SDK for automatic tracing."""
    try:
        from azure.ai.projects.telemetry import AIProjectsInstrumentor
        AIProjectsInstrumentor().instrument(
            enable_content_recording=enable_content_recording
        )
        logger.info("✅ Azure AI Projects SDK instrumented")
    except ImportError:
        logger.debug("Azure AI Projects telemetry not available")
    except Exception as e:
        logger.warning(f"Failed to instrument Azure AI Projects: {e}")


def _add_trace_counter() -> None:
    """Add a span processor that counts traces."""
    global _trace_count
    
    try:
        from opentelemetry import trace as otel_trace
        from opentelemetry.sdk.trace import SpanProcessor
        
        class CountingProcessor(SpanProcessor):
            def on_start(self, span, parent_context=None):
                pass
            
            def on_end(self, span):
                global _trace_count
                _trace_count += 1
            
            def shutdown(self):
                pass
            
            def force_flush(self, timeout_millis=30000):
                return True
        
        provider = otel_trace.get_tracer_provider()
        if hasattr(provider, 'add_span_processor'):
            provider.add_span_processor(CountingProcessor())
            
    except Exception as e:
        logger.debug(f"Could not add trace counter: {e}")


def is_tracing_enabled() -> bool:
    """Check if tracing has been initialized."""
    return _tracing_initialized


def get_trace_count() -> int:
    """Get the number of traces recorded."""
    return _trace_count


def reset_trace_count() -> None:
    """Reset the trace counter."""
    global _trace_count
    _trace_count = 0


def get_tracer(name: str = __name__):
    """
    Get an OpenTelemetry tracer for manual span creation.
    
    Usage:
        tracer = get_tracer(__name__)
        with tracer.start_as_current_span("my_operation") as span:
            span.set_attribute("custom.attribute", "value")
            # ... your code ...
    """
    from opentelemetry import trace as otel_trace
    return otel_trace.get_tracer(name)


def trace_agent_call(func):
    """
    Decorator to trace agent/LLM calls with automatic span creation.
    
    Usage:
        @trace_agent_call
        async def call_agent(self, prompt: str) -> str:
            ...
    """
    import functools
    from opentelemetry import trace as otel_trace
    
    tracer = otel_trace.get_tracer(__name__)
    
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        with tracer.start_as_current_span(
            f"agent.{func.__name__}",
            kind=otel_trace.SpanKind.CLIENT
        ) as span:
            # Add function arguments as attributes
            if args and hasattr(args[0], '__class__'):
                span.set_attribute("agent.class", args[0].__class__.__name__)
            
            try:
                result = await func(*args, **kwargs)
                span.set_status(otel_trace.StatusCode.OK)
                return result
            except Exception as e:
                span.set_status(otel_trace.StatusCode.ERROR, str(e))
                span.record_exception(e)
                raise
    
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        with tracer.start_as_current_span(
            f"agent.{func.__name__}",
            kind=otel_trace.SpanKind.CLIENT
        ) as span:
            if args and hasattr(args[0], '__class__'):
                span.set_attribute("agent.class", args[0].__class__.__name__)
            
            try:
                result = func(*args, **kwargs)
                span.set_status(otel_trace.StatusCode.OK)
                return result
            except Exception as e:
                span.set_status(otel_trace.StatusCode.ERROR, str(e))
                span.record_exception(e)
                raise
    
    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper
