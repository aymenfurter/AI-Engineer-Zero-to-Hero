"""Executors for the NASA slideshow workflow."""
from typing import Optional
from agent_framework import ChatAgent, Executor, WorkflowContext, handler, ChatMessage, Role

from state import SlideWorkflowState
from models import ImageSelection, ReviewResult, FinalSlide, NASAImage
from nasa_api import search_nasa_images, format_images_summary


# Constants
MAX_ATTEMPTS = 10  # Retry up to 10 times before using judge
MAX_SEARCH_RESULTS = 8
MAX_CANDIDATES_FOR_SELECTION = 5


class SearchExecutor(Executor):
    """Searches NASA API for candidate images based on the current query."""

    def __init__(self, id: str = "search"):
        super().__init__(id=id)
    
    @handler
    async def handle(
        self,
        state: SlideWorkflowState,
        ctx: WorkflowContext[SlideWorkflowState]
    ) -> None:
        """Execute the search phase."""
        state.emit_event(
            "search_started",
            position=state.position,
            attempt=state.current_attempt + 1,
            subject=state.outline_item.subject
        )
        
        # Determine search query
        query = self._determine_search_query(state)
        state.record_search(query)
        
        # Search NASA API
        try:
            results = await search_nasa_images(query, page_size=MAX_SEARCH_RESULTS)
            state.current_candidates = state.filter_unused_candidates(results)
        except Exception as e:
            state.emit_event("search_error", error=str(e))
            state.current_candidates = []
        
        state.emit_event(
            "search_completed",
            query=query,
            result_count=len(state.current_candidates),
            candidates=[{
                "nasa_id": c.nasa_id,
                "title": c.title,
                "thumbnail_url": c.thumbnail_url
            } for c in state.current_candidates[:5]]
        )
        
        # Transition to next phase
        if state.current_candidates:
            state.phase = "select"
        else:
            # No results - retry with simpler query if we have attempts left
            state.current_attempt += 1
            if state.current_attempt < state.max_attempts:
                state.phase = "search"  # Retry with different keywords
                state.emit_event(
                    "search_retry",
                    message=f"No results, trying simpler query (attempt {state.current_attempt + 1})"
                )
            else:
                state.phase = "done"  # Give up after max attempts
        
        await ctx.send_message(state)
    
    def _determine_search_query(self, state: SlideWorkflowState) -> str:
        """Determine the search query based on current state."""
        keywords = state.outline_item.search_keywords or []
        subject = state.outline_item.subject
        
        # First attempt: use subject + first keyword
        if state.current_attempt == 0:
            if keywords:
                return f"{subject} {keywords[0]}"
            return subject
        
        # Second attempt: just the subject alone
        if state.current_attempt == 1:
            return subject
        
        # Third attempt: try another keyword if available
        if state.current_attempt == 2:
            if len(keywords) > 1:
                return keywords[1]
            return subject.split()[0] if ' ' in subject else subject
        
        # Fallback: cycle through remaining keywords
        if keywords:
            idx = state.current_attempt % len(keywords)
            return keywords[idx]
        
        return subject


class SelectExecutor(Executor):
    """Selects the best image from candidates using an LLM agent."""

    def __init__(self, researcher_agent: ChatAgent, id: str = "select"):
        super().__init__(id=id)
        self._researcher_agent = researcher_agent
    
    @handler
    async def handle(
        self,
        state: SlideWorkflowState,
        ctx: WorkflowContext[SlideWorkflowState]
    ) -> None:
        """Select an image from candidates."""
        state.emit_event(
            "selection_started",
            position=state.position,
            candidate_count=len(state.current_candidates)
        )
        
        # Check if we should go to judge
        if state.has_exceeded_max_attempts:
            state.phase = "judge"
            await ctx.send_message(state)
            return
        
        # No candidates? Go back to search or end
        if not state.current_candidates:
            state.current_attempt += 1
            state.phase = "search" if state.current_attempt < state.max_attempts else "done"
            await ctx.send_message(state)
            return
        
        # Build prompt for researcher
        prompt = self._build_selection_prompt(state)
        
        try:
            response = await self._researcher_agent.run(
                [ChatMessage(role=Role.USER, text=prompt)],
                response_format=ImageSelection
            )
            
            if response.value:
                selection = response.value
                # Find the full image data
                image_data = self._find_image(selection.nasa_id, state.current_candidates)
                if image_data:
                    selection.thumbnail_url = image_data.thumbnail_url
                
                state.current_selection = selection
                state.emit_event(
                    "image_selected",
                    nasa_id=selection.nasa_id,
                    title=selection.title,
                    reason=selection.reason,
                    thumbnail_url=selection.thumbnail_url
                )
                state.phase = "review"
            else:
                state.current_attempt += 1
                state.phase = "search"
                
        except Exception as e:
            state.emit_event("selection_error", error=str(e))
            state.current_attempt += 1
            state.phase = "search"
        
        await ctx.send_message(state)
    
    def _build_selection_prompt(self, state: SlideWorkflowState) -> str:
        """Build the prompt for image selection."""
        item = state.outline_item
        outline = state.full_outline
        
        candidates_text = format_images_summary(
            state.current_candidates[:MAX_CANDIDATES_FOR_SELECTION]
        )
        
        prompt = f"""PRESENTATION: {outline.title}
Narrative: {outline.narrative}

SLIDE REQUIREMENT:
Position: {item.position} of {len(outline.slides)}
Subject: {item.subject}
Topic: {item.topic}
Purpose: {item.purpose}
Search Keywords: {', '.join(item.search_keywords)}

CANDIDATE IMAGES:
{candidates_text}

Select the BEST matching image for this slide."""

        # Add previous attempt feedback
        if state.conversation_history:
            prompt += "\n\nPREVIOUS ATTEMPTS (avoid these issues):"
            for attempt in state.conversation_history:
                prompt += f"\n- {attempt['selected']['title']}: {attempt['review']['feedback']}"
        
        return prompt
    
    def _find_image(self, nasa_id: str, candidates: list[NASAImage]) -> Optional[NASAImage]:
        """Find an image by NASA ID in the candidates list."""
        for img in candidates:
            if img.nasa_id == nasa_id:
                return img
        return None


class ReviewExecutor(Executor):
    """Reviews selected images for quality and relevance."""

    def __init__(self, reviewer_agent: ChatAgent, id: str = "review"):
        super().__init__(id=id)
        self._reviewer_agent = reviewer_agent
    
    @handler
    async def handle(
        self,
        state: SlideWorkflowState,
        ctx: WorkflowContext[SlideWorkflowState]
    ) -> None:
        """Review the selected image."""
        if not state.current_selection:
            state.phase = "search"
            await ctx.send_message(state)
            return
        
        state.emit_event(
            "review_started",
            position=state.position,
            nasa_id=state.current_selection.nasa_id,
            title=state.current_selection.title
        )
        
        # Build review prompt
        prompt = self._build_review_prompt(state)
        
        try:
            response = await self._reviewer_agent.run(
                [ChatMessage(role=Role.USER, text=prompt)],
                response_format=ReviewResult
            )
            
            if response.value:
                review = response.value
                
                # Record the attempt
                state.record_attempt(
                    selection=state.current_selection,
                    approved=review.approved,
                    feedback=review.feedback
                )
                
                state.emit_event(
                    "review_completed",
                    approved=review.approved,
                    feedback=review.feedback,
                    issues=review.issues,
                    search_suggestion=review.search_suggestion
                )
                
                if review.approved:
                    # Success! Create final slide
                    state.selected_image = FinalSlide(
                        position=state.outline_item.position,
                        subject=state.outline_item.subject,
                        topic=state.outline_item.topic,
                        image=state.current_selection,
                        thumbnail_url=state.current_selection.thumbnail_url
                    )
                    state.mark_image_used(state.current_selection.nasa_id)
                    state.phase = "done"
                    await ctx.yield_output(state)
                    return
                else:
                    # Rejected - try again
                    state.current_selection = None
                    state.current_attempt += 1
                    
                    if state.has_exceeded_max_attempts:
                        state.phase = "judge"
                    else:
                        state.phase = "search"
            else:
                state.current_attempt += 1
                state.phase = "search"
                
        except Exception as e:
            state.emit_event("review_error", error=str(e))
            state.current_attempt += 1
            state.phase = "search" if state.current_attempt < state.max_attempts else "judge"
        
        await ctx.send_message(state)
    
    def _build_review_prompt(self, state: SlideWorkflowState) -> str:
        """Build the prompt for image review."""
        item = state.outline_item
        selection = state.current_selection
        
        # Find full image data for more context
        image_data = None
        for img in state.current_candidates:
            if img.nasa_id == selection.nasa_id:
                image_data = img
                break
        
        description = image_data.description if image_data else "No description available"
        keywords = ", ".join(image_data.keywords) if image_data else "None"
        
        prev_searches = ""
        if state.previous_searches:
            prev_searches = f"\n\nPREVIOUS SEARCHES (do NOT suggest these again):\n- " + "\n- ".join(state.previous_searches)
        
        return f"""PRESENTATION: {state.full_outline.title}

=== SLIDE REQUIREMENT (MUST MATCH) ===
Position: {item.position}
Subject: {item.subject}
Topic: {item.topic}
Purpose: {item.purpose}

=== CRITICAL VALIDATION ===
The slide topic says: "{item.topic}"
You MUST verify the image actually SHOWS this content.

For example:
- If topic says "as a circle/sphere" → image must show full disc view, NOT surface closeup
- If topic says "surface features" → image must show surface, NOT distant view
- If topic says "astronaut" → must show actual astronaut, not just spacecraft

=== SELECTED IMAGE ===
NASA ID: {selection.nasa_id}
Title: {selection.title}
Description: {description}
Keywords: {keywords}
Selection Reason: {selection.reason}{prev_searches}

=== YOUR TASK ===
Carefully verify: Does this image VISUALLY match what "{item.topic}" requires?
Be STRICT - reject if the visual content doesn't match the topic description."""


class JudgeExecutor(Executor):
    """Final arbiter that picks the best image from all attempted candidates."""

    def __init__(self, judge_agent: ChatAgent, id: str = "judge"):
        super().__init__(id=id)
        self._judge_agent = judge_agent
    
    @handler
    async def handle(
        self,
        state: SlideWorkflowState,
        ctx: WorkflowContext[SlideWorkflowState]
    ) -> None:
        """Pick the best image from all previous attempts."""
        state.emit_event(
            "judge_started",
            position=state.position,
            attempt_count=len(state.conversation_history)
        )
        
        if not state.conversation_history:
            # No attempts to judge, end workflow
            state.phase = "done"
            await ctx.yield_output(state)
            return
        
        # Build judge prompt
        prompt = self._build_judge_prompt(state)
        
        try:
            response = await self._judge_agent.run(
                [ChatMessage(role=Role.USER, text=prompt)],
                response_format=ImageSelection
            )
            
            if response.value:
                selection = response.value
                
                # Find thumbnail from history
                thumbnail_url = None
                for attempt in state.conversation_history:
                    if attempt["selected"]["nasa_id"] == selection.nasa_id:
                        # Try to find in candidates
                        for img in state.current_candidates:
                            if img.nasa_id == selection.nasa_id:
                                thumbnail_url = img.thumbnail_url
                                break
                        break
                
                state.selected_image = FinalSlide(
                    position=state.outline_item.position,
                    subject=state.outline_item.subject,
                    topic=state.outline_item.topic,
                    image=ImageSelection(
                        nasa_id=selection.nasa_id,
                        title=selection.title,
                        reason=f"Judge selected: {selection.reason}",
                        thumbnail_url=thumbnail_url
                    ),
                    thumbnail_url=thumbnail_url
                )
                state.mark_image_used(selection.nasa_id)
                
                state.emit_event(
                    "judge_selected",
                    nasa_id=selection.nasa_id,
                    title=selection.title,
                    reason=selection.reason
                )
                
        except Exception as e:
            state.emit_event("judge_error", error=str(e))
            
            # Fallback: use the first attempted image
            if state.conversation_history:
                fallback = state.conversation_history[0]["selected"]
                state.selected_image = FinalSlide(
                    position=state.outline_item.position,
                    subject=state.outline_item.subject,
                    topic=state.outline_item.topic,
                    image=ImageSelection(
                        nasa_id=fallback["nasa_id"],
                        title=fallback["title"],
                        reason="Fallback selection"
                    )
                )
        
        state.phase = "done"
        await ctx.yield_output(state)
    
    def _build_judge_prompt(self, state: SlideWorkflowState) -> str:
        """Build the prompt for final judgment."""
        item = state.outline_item
        
        candidates_text = []
        for i, attempt in enumerate(state.conversation_history, 1):
            sel = attempt["selected"]
            review = attempt["review"]
            candidates_text.append(
                f"CANDIDATE {i}: {sel['nasa_id']}\n"
                f"  Title: {sel['title']}\n"
                f"  Original Reason: {sel['reason']}\n"
                f"  Feedback: {review['feedback']}"
            )
        
        return f"""SLIDE REQUIREMENT:
Subject: {item.subject}
Topic: {item.topic}
Purpose: {item.purpose}

ATTEMPTED IMAGES:
{chr(10).join(candidates_text)}

Pick the BEST image from these options (the least problematic one).
You MUST select one - do not reject all options."""
