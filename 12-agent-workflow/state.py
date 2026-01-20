"""Workflow state for NASA slideshow selection."""
from typing import Optional, Callable, Any
from pydantic import BaseModel, Field

from models import (
    SlideOutlineItem,
    PresentationOutline,
    NASAImage,
    ImageSelection,
    FinalSlide
)


class SlideWorkflowState(BaseModel):
    """State that flows through all executors in the workflow graph."""
    model_config = {"arbitrary_types_allowed": True}
    
    # Input context
    outline_item: SlideOutlineItem
    full_outline: PresentationOutline
    
    # Search tracking
    current_search_query: str = ""
    current_candidates: list[NASAImage] = Field(default_factory=list)
    previous_searches: list[str] = Field(default_factory=list)
    
    # Selection tracking
    current_attempt: int = 0
    max_attempts: int = 10  # Retry up to 10 times before using judge
    current_selection: Optional[ImageSelection] = None
    conversation_history: list[dict] = Field(default_factory=list)
    
    # Output
    selected_image: Optional[FinalSlide] = None
    phase: str = "search"  # search, select, review, done
    
    # Already used images (to avoid duplicates)
    already_selected_ids: set[str] = Field(default_factory=set)
    
    # Event tracking for UI
    events: list[dict] = Field(default_factory=list)
    event_callback: Optional[Callable[[dict], Any]] = Field(default=None, exclude=True)
    
    def emit_event(self, event_type: str, **data) -> None:
        """Emit an event for UI tracking."""
        event = {"type": event_type, **data}
        self.events.append(event)
        if self.event_callback:
            self.event_callback(event)
    
    @property
    def position(self) -> int:
        """Convenience accessor for the current slide position."""
        return self.outline_item.position
    
    @property
    def has_exceeded_max_attempts(self) -> bool:
        """Check if we've exceeded the maximum retry attempts."""
        return self.current_attempt >= self.max_attempts
    
    def record_search(self, query: str) -> None:
        """Record a search query to avoid duplicates."""
        self.current_search_query = query
        if query not in self.previous_searches:
            self.previous_searches.append(query)
    
    def record_attempt(self, selection: ImageSelection, approved: bool, feedback: str) -> None:
        """Record a selection attempt in the conversation history."""
        self.conversation_history.append({
            "attempt": self.current_attempt + 1,
            "search_query": self.current_search_query,
            "selected": {
                "nasa_id": selection.nasa_id,
                "title": selection.title,
                "reason": selection.reason
            },
            "review": {
                "approved": approved,
                "feedback": feedback
            }
        })
    
    def mark_image_used(self, nasa_id: str) -> None:
        """Mark an image as used to prevent duplicates."""
        self.already_selected_ids.add(nasa_id)
    
    def filter_unused_candidates(self, candidates: list[NASAImage]) -> list[NASAImage]:
        """Filter out already-used images from candidates."""
        return [c for c in candidates if c.nasa_id not in self.already_selected_ids]
