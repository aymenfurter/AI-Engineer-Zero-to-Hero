"""Pydantic models for structured agent outputs in the NASA slideshow workflow."""
from typing import Optional
from pydantic import BaseModel, Field


class SlideOutlineItem(BaseModel):
    """A single slide in the presentation outline."""
    position: int = Field(..., description="Position in the deck (1-based)")
    subject: str = Field(..., description="Main subject of this slide (e.g., mission name, spacecraft, astronaut, event)")
    topic: str = Field(..., description="What aspect or detail to show")
    search_keywords: list[str] = Field(default_factory=list, description="Keywords for NASA image search")
    purpose: str = Field(..., description="Why this slide is needed in the flow")


class PresentationOutline(BaseModel):
    """Structured outline for a NASA-themed presentation."""
    title: str = Field(..., description="Overall presentation title")
    narrative: str = Field(..., description="Brief story arc description")
    slides: list[SlideOutlineItem] = Field(..., description="Ordered list of slides needed")


class NASAImage(BaseModel):
    """A NASA image from the API."""
    nasa_id: str = Field(..., description="Unique NASA identifier")
    title: str = Field(..., description="Image title")
    description: str = Field(default="", description="Image description")
    date_created: str = Field(default="", description="When the image was created")
    center: str = Field(default="", description="NASA center that created it")
    keywords: list[str] = Field(default_factory=list, description="Associated keywords")
    thumbnail_url: Optional[str] = Field(None, description="URL to thumbnail image")
    preview_url: Optional[str] = Field(None, description="URL to preview image")


class ImageSelection(BaseModel):
    """An image selected by the researcher agent."""
    nasa_id: str = Field(..., description="NASA ID of selected image")
    title: str = Field(..., description="Image title")
    reason: str = Field(..., description="Why this image was selected")
    thumbnail_url: Optional[str] = Field(None, description="Thumbnail URL")


class ReviewResult(BaseModel):
    """Result from the reviewer agent evaluation."""
    approved: bool = Field(..., description="Whether the image is approved for the slide")
    feedback: str = Field(..., description="Detailed feedback on the image selection")
    issues: list[str] = Field(default_factory=list, description="Specific issues found")
    search_suggestion: Optional[str] = Field(None, description="Suggested search query if rejected")


class FinalSlide(BaseModel):
    """A completed slide with approved image."""
    position: int = Field(..., description="Position in the deck")
    subject: str = Field(..., description="Main subject featured")
    topic: str = Field(..., description="Topic covered")
    image: ImageSelection = Field(..., description="Selected NASA image")
    thumbnail_url: Optional[str] = Field(None, description="Image thumbnail URL")
