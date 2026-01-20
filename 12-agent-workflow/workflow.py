"""Workflow definition for NASA slideshow using Microsoft Agent Framework."""
from agent_framework import ChatAgent, Workflow, WorkflowBuilder

from executors import SearchExecutor, SelectExecutor, ReviewExecutor, JudgeExecutor


def create_slideshow_workflow(
    researcher_agent: ChatAgent,
    reviewer_agent: ChatAgent,
    judge_agent: ChatAgent,
    max_iterations: int = 12
) -> Workflow:
    search = SearchExecutor()
    select = SelectExecutor(researcher_agent)
    review = ReviewExecutor(reviewer_agent)
    judge = JudgeExecutor(judge_agent)
    
    # Build workflow graph
    builder = WorkflowBuilder()
    
    # Search → Select (when candidates found)
    builder.add_edge(
        search,
        select,
        condition=lambda s: s.phase == "select"
    )
    
    # Search → Done (no results)
    # This is implicit - workflow ends when no more transitions
    
    # Select → Review (image selected)
    builder.add_edge(
        select,
        review,
        condition=lambda s: s.phase == "review"
    )
    
    # Select → Judge (max attempts exceeded)
    builder.add_edge(
        select,
        judge,
        condition=lambda s: s.phase == "judge"
    )
    
    # Select → Search (retry needed)
    builder.add_edge(
        select,
        search,
        condition=lambda s: s.phase == "search"
    )
    
    # Review → Search (rejected, retry)
    builder.add_edge(
        review,
        search,
        condition=lambda s: s.phase == "search"
    )
    
    # Review → Judge (max attempts, need final decision)
    builder.add_edge(
        review,
        judge,
        condition=lambda s: s.phase == "judge"
    )
    
    # Review → Done (approved) - implicit via yield_output
    
    # Set entry point and limits
    builder.set_start_executor(search)
    builder.set_max_iterations(max_iterations)
    
    return builder.build()


# Alias for backwards compatibility
build_slideshow_workflow = create_slideshow_workflow
