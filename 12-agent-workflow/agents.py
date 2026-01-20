"""Agent orchestration for NASA slideshow building using APIM Gateway."""
import asyncio
from typing import AsyncIterator, Optional, Callable, Any

from agent_framework import ChatMessage, Role
from agent_framework.openai import OpenAIChatClient

from models import PresentationOutline, SlideOutlineItem, FinalSlide
from prompts import (
    PLANNER_AGENT_INSTRUCTIONS,
    RESEARCHER_AGENT_INSTRUCTIONS,
    REVIEWER_AGENT_INSTRUCTIONS,
    JUDGE_AGENT_INSTRUCTIONS,
)
from state import SlideWorkflowState
from workflow import create_slideshow_workflow


class SlideshowOrchestrator:
    """
    Orchestrates the multi-agent workflow for building NASA image slideshows.
    
    Uses the Landing Zone APIM Gateway for LLM access (centralized model management).
    
    This orchestrator manages three main phases:
    1. Planning - Generate a structured presentation outline
    2. Image Selection - For each slide, run the search/select/review workflow
    3. Assembly - Collect all approved slides into the final presentation
    
    Agents:
    - Planner: Creates the presentation outline
    - Researcher: Selects best images from NASA search results
    - Reviewer: Validates image relevance and quality
    - Judge: Final arbiter when max attempts reached
    """
    
    def __init__(
        self,
        apim_endpoint: str,
        apim_key: str,
        deployment_name: str = "gpt-4.1-mini",
        api_version: str = "2024-10-21"
    ):
        """
        Initialize the orchestrator with APIM Gateway configuration.
        
        This uses the centralized Landing Zone pattern where all LLM access
        goes through Azure API Management for governance and cost tracking.
        
        Args:
            apim_endpoint: APIM Gateway endpoint (e.g., https://apim-xxx.azure-api.net)
            apim_key: APIM subscription key for authentication
            deployment_name: Model deployment name (default: gpt-4.1-mini)
            api_version: API version to use
        """
        # Configure OpenAI client to use APIM as the base URL
        # APIM acts as a proxy to Azure OpenAI with API key auth
        # Note: apim_endpoint already includes /openai (e.g., https://xxx.azure-api.net/openai)
        # APIM requires the subscription key in a custom header, not as Bearer token
        self._chat_client = OpenAIChatClient(
            model_id=deployment_name,
            api_key="placeholder",  # Required but not used - APIM uses header
            base_url=f"{apim_endpoint}/deployments/{deployment_name}",
            default_headers={
                "api-key": apim_key,  # Azure OpenAI style header for APIM
            },
        )
        self._model = deployment_name
        
        # Create specialized agents
        self._planner_agent = self._chat_client.create_agent(
            name="PlannerAgent",
            instructions=PLANNER_AGENT_INSTRUCTIONS,
            model=deployment_name,
        )
        
        self._researcher_agent = self._chat_client.create_agent(
            name="ResearcherAgent",
            instructions=RESEARCHER_AGENT_INSTRUCTIONS,
            model=deployment_name,
        )
        
        self._reviewer_agent = self._chat_client.create_agent(
            name="ReviewerAgent",
            instructions=REVIEWER_AGENT_INSTRUCTIONS,
            model=deployment_name,
        )
        
        self._judge_agent = self._chat_client.create_agent(
            name="JudgeAgent",
            instructions=JUDGE_AGENT_INSTRUCTIONS,
            model=deployment_name,
        )
        
        # Create the workflow
        self._workflow = create_slideshow_workflow(
            researcher_agent=self._researcher_agent,
            reviewer_agent=self._reviewer_agent,
            judge_agent=self._judge_agent,
        )
    
    async def generate_outline(
        self,
        user_request: str
    ) -> PresentationOutline:
        """
        Generate a structured presentation outline for the given request.
        
        Args:
            user_request: User's description of what presentation they want
            
        Returns:
            PresentationOutline with title, narrative, and slide specifications
        """
        prompt = f"""Create a presentation outline for the following request:

{user_request}

Remember:
- Include 5-8 slides
- Each slide should focus on one aspect that can be illustrated with a NASA image
- Provide specific search keywords for each slide"""

        response = await self._planner_agent.run(
            [ChatMessage(role=Role.USER, text=prompt)],
            response_format=PresentationOutline
        )
        
        if response.value:
            return response.value
        
        raise ValueError("Failed to generate presentation outline")
    
    async def select_image_for_slide(
        self,
        outline_item: SlideOutlineItem,
        full_outline: PresentationOutline,
        already_selected_ids: set[str],
        event_callback: Optional[Callable[[dict], Any]] = None
    ) -> AsyncIterator[dict]:
        """
        Run the image selection workflow for a single slide.
        
        This runs the search → select → review cycle until an image
        is approved or max attempts is reached.
        
        Args:
            outline_item: The slide specification
            full_outline: Full presentation context
            already_selected_ids: Set of NASA IDs already used
            event_callback: Optional callback for real-time events
            
        Yields:
            Event dictionaries for progress tracking
            Final event contains the selected image
        """
        # Create event queue for streaming
        event_queue: asyncio.Queue[dict] = asyncio.Queue()
        
        def queue_event(event: dict) -> None:
            event_queue.put_nowait(event)
        
        # Initialize workflow state
        initial_state = SlideWorkflowState(
            outline_item=outline_item,
            full_outline=full_outline,
            already_selected_ids=already_selected_ids.copy(),
            event_callback=queue_event
        )
        
        # Run workflow in background
        workflow_task = asyncio.create_task(self._workflow.run(initial_state))
        
        # Stream events while workflow runs
        while not workflow_task.done():
            try:
                event = await asyncio.wait_for(event_queue.get(), timeout=0.1)
                if event_callback:
                    event_callback(event)
                yield event
            except asyncio.TimeoutError:
                continue
        
        # Drain remaining events
        while not event_queue.empty():
            event = event_queue.get_nowait()
            if event_callback:
                event_callback(event)
            yield event
        
        # Get final result
        result = await workflow_task
        outputs = result.get_outputs()
        
        final_slide = None
        if outputs:
            for output in outputs:
                if isinstance(output, SlideWorkflowState) and output.selected_image:
                    final_slide = output.selected_image
                    break
        
        # Yield final result
        yield {
            "type": "slide_complete",
            "position": outline_item.position,
            "slide": final_slide.model_dump() if final_slide else None
        }
    
    async def build_slideshow(
        self,
        user_request: str,
        event_callback: Optional[Callable[[dict], Any]] = None
    ) -> AsyncIterator[dict]:
        """
        Build a complete slideshow from a user request.
        
        This orchestrates the full workflow:
        1. Generate presentation outline
        2. For each slide, run image selection workflow
        3. Collect and return final slideshow
        
        Args:
            user_request: User's description of desired presentation
            event_callback: Optional callback for real-time events
            
        Yields:
            Event dictionaries tracking progress
            Final event contains complete slideshow
        """
        def emit(event: dict) -> None:
            if event_callback:
                event_callback(event)
        
        # Phase 1: Generate Outline
        yield {"type": "phase", "phase": "planning", "message": "Creating presentation outline..."}
        
        try:
            outline = await self.generate_outline(user_request)
            yield {
                "type": "outline_ready",
                "title": outline.title,
                "narrative": outline.narrative,
                "slides": [s.model_dump() for s in outline.slides]
            }
        except Exception as e:
            yield {"type": "error", "phase": "planning", "message": str(e)}
            return
        
        # Phase 2: Select Images for Each Slide
        yield {
            "type": "phase",
            "phase": "image_selection",
            "message": f"Selecting images for {len(outline.slides)} slides..."
        }
        
        final_slides: list[FinalSlide] = []
        already_selected: set[str] = set()
        
        for slide_spec in outline.slides:
            yield {
                "type": "slide_started",
                "position": slide_spec.position,
                "subject": slide_spec.subject,
                "topic": slide_spec.topic,
                "total": len(outline.slides)
            }
            
            # Run workflow for this slide
            selected_slide = None
            async for event in self.select_image_for_slide(
                outline_item=slide_spec,
                full_outline=outline,
                already_selected_ids=already_selected,
                event_callback=event_callback
            ):
                yield event
                
                if event.get("type") == "slide_complete":
                    slide_data = event.get("slide")
                    if slide_data:
                        selected_slide = FinalSlide(**slide_data)
            
            if selected_slide:
                final_slides.append(selected_slide)
                already_selected.add(selected_slide.image.nasa_id)
                yield {
                    "type": "slide_selected",
                    "position": slide_spec.position,
                    "nasa_id": selected_slide.image.nasa_id,
                    "title": selected_slide.image.title,
                    "thumbnail_url": selected_slide.thumbnail_url
                }
            else:
                yield {
                    "type": "slide_failed",
                    "position": slide_spec.position,
                    "message": f"Could not find suitable image for {slide_spec.topic}"
                }
        
        # Phase 3: Return Complete Slideshow
        yield {
            "type": "phase",
            "phase": "complete",
            "message": f"Slideshow complete with {len(final_slides)} slides!"
        }
        
        yield {
            "type": "slideshow_complete",
            "title": outline.title,
            "narrative": outline.narrative,
            "slides": [s.model_dump() for s in final_slides],
            "total_slides": len(final_slides)
        }
