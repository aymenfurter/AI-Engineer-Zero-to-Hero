"""Debug event emission for workflow observability."""
import time
from typing import Callable, Any, Optional
from dataclasses import dataclass, field


@dataclass
class DebugEventEmitter:
    """
    Centralized event emission for workflow debugging and UI updates.
    
    This class provides a clean API for executors to emit events without
    cluttering their business logic. Events can be consumed by:
    - UI components for real-time updates
    - Tracing systems for distributed tracing
    - Logging for debugging
    
    Usage:
        emitter = DebugEventEmitter(callback=my_callback)
        emitter.llm_call_started("PlannerAgent", "Generate outline", prompt)
        # ... do work ...
        emitter.llm_call_completed("PlannerAgent", duration_ms, response_preview)
    """
    callback: Optional[Callable[[dict], Any]] = None
    events: list = field(default_factory=list)
    
    # Preview length limits
    PROMPT_PREVIEW_LENGTH: int = 500
    RESPONSE_PREVIEW_LENGTH: int = 300
    QUERY_PREVIEW_LENGTH: int = 100
    
    def _emit(self, event_type: str, **data) -> None:
        """Emit an event to the callback and store it."""
        event = {"type": event_type, "timestamp": time.time(), **data}
        self.events.append(event)
        if self.callback:
            self.callback(event)
    
    # =========================================================================
    # Workflow Phase Events
    # =========================================================================
    
    def workflow_started(self, name: str, total_steps: int = 0, **details) -> None:
        """Emit workflow started event."""
        self._emit("workflow_started", name=name, total_steps=total_steps, **details)
    
    def workflow_completed(self, name: str, success: bool = True, **details) -> None:
        """Emit workflow completed event."""
        self._emit("workflow_completed", name=name, success=success, **details)
    
    def phase_started(self, phase: str, description: str = "", **details) -> None:
        """Emit phase started event."""
        self._emit("phase_started", phase=phase, description=description, **details)
    
    def phase_completed(self, phase: str, success: bool = True, **details) -> None:
        """Emit phase completed event."""
        self._emit("phase_completed", phase=phase, success=success, **details)
    
    # =========================================================================
    # LLM Call Events (for agent observability)
    # =========================================================================
    
    def llm_call_started(
        self,
        agent: str,
        task: str,
        prompt_preview: str,
        response_format: str = "text",
        **details
    ) -> None:
        """Emit LLM call started event."""
        self._emit(
            "llm_call_started",
            agent=agent,
            task=task,
            prompt_preview=self._truncate(prompt_preview, self.PROMPT_PREVIEW_LENGTH),
            response_format=response_format,
            **details
        )
    
    def llm_call_completed(
        self,
        agent: str,
        duration_ms: int,
        response_preview: str,
        success: bool = True,
        **details
    ) -> None:
        """Emit LLM call completed event."""
        self._emit(
            "llm_call_completed",
            agent=agent,
            duration_ms=duration_ms,
            response_preview=self._truncate(response_preview, self.RESPONSE_PREVIEW_LENGTH),
            success=success,
            **details
        )
    
    def llm_call_failed(
        self,
        agent: str,
        duration_ms: int,
        error: str,
        **details
    ) -> None:
        """Emit LLM call failed event."""
        self._emit(
            "llm_call_failed",
            agent=agent,
            duration_ms=duration_ms,
            error=error,
            success=False,
            **details
        )
    
    # =========================================================================
    # Search Events
    # =========================================================================
    
    def search_started(self, query: str, **details) -> None:
        """Emit search started event."""
        self._emit(
            "search_started",
            query=self._truncate(query, self.QUERY_PREVIEW_LENGTH),
            **details
        )
    
    def search_completed(
        self,
        query: str,
        result_count: int,
        duration_ms: int,
        results_preview: list = None,
        **details
    ) -> None:
        """Emit search completed event."""
        self._emit(
            "search_completed",
            query=query,
            result_count=result_count,
            duration_ms=duration_ms,
            results=results_preview[:6] if results_preview else [],
            **details
        )
    
    # =========================================================================
    # Selection/Review Events (for workflows with critique loops)
    # =========================================================================
    
    def selection_made(
        self,
        position: int,
        selected_id: str,
        reason: str,
        **details
    ) -> None:
        """Emit selection made event."""
        self._emit(
            "selection_made",
            position=position,
            selected_id=selected_id,
            reason=reason,
            **details
        )
    
    def review_completed(
        self,
        position: int,
        approved: bool,
        feedback: str,
        **details
    ) -> None:
        """Emit review completed event."""
        self._emit(
            "review_completed",
            position=position,
            approved=approved,
            feedback=self._truncate(feedback, self.RESPONSE_PREVIEW_LENGTH),
            **details
        )
    
    def judge_invoked(
        self,
        position: int,
        candidates_count: int,
        selected_id: str,
        reason: str,
        **details
    ) -> None:
        """Emit judge invoked event."""
        self._emit(
            "judge_invoked",
            position=position,
            candidates_count=candidates_count,
            selected_id=selected_id,
            reason=reason,
            **details
        )
    
    # =========================================================================
    # Edge Transition Events (for workflow graph visualization)
    # =========================================================================
    
    def edge_transition(
        self,
        from_node: str,
        to_node: str,
        condition: str,
        **details
    ) -> None:
        """Emit workflow edge transition event."""
        self._emit(
            "edge_transition",
            from_node=from_node,
            to_node=to_node,
            condition=condition,
            **details
        )
    
    # =========================================================================
    # Generic Events
    # =========================================================================
    
    def custom_event(self, event_type: str, **data) -> None:
        """Emit a custom event."""
        self._emit(event_type, **data)
    
    def _truncate(self, text: str, max_length: int) -> str:
        """Truncate text with ellipsis if too long."""
        if not text:
            return ""
        return text if len(text) <= max_length else text[:max_length] + "..."


def create_debug_emitter(callback: Optional[Callable[[dict], Any]] = None) -> DebugEventEmitter:
    """Factory function to create a debug event emitter."""
    return DebugEventEmitter(callback=callback)
