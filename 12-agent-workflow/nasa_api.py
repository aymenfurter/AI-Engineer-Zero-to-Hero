"""NASA Images API integration for the slideshow workflow."""
import httpx
from typing import Optional
from models import NASAImage

NASA_API_BASE = "https://images-api.nasa.gov"
DEFAULT_YEAR_START = 1960
DEFAULT_YEAR_END = 2026


async def search_nasa_images(
    query: str,
    media_type: str = "image",
    year_start: int = DEFAULT_YEAR_START,
    year_end: int = DEFAULT_YEAR_END,
    page: int = 1,
    page_size: int = 10
) -> list[NASAImage]:
    """
    Search NASA Images API for images matching the query.
    
    Args:
        query: Search terms (e.g., "mars surface", "jupiter storm")
        media_type: Type of media ("image", "video", "audio")
        year_start: Earliest year for results
        year_end: Latest year for results
        page: Page number for pagination
        page_size: Number of results to return (max from first page)
    
    Returns:
        List of NASAImage objects
    """
    url = f"{NASA_API_BASE}/search"
    params = {
        "q": query,
        "media_type": media_type,
        "year_start": year_start,
        "year_end": year_end,
        "page": page
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
    
    images = []
    items = data.get("collection", {}).get("items", [])[:page_size]
    
    for item in items:
        # Extract metadata from the first data entry
        item_data = item.get("data", [{}])[0]
        
        # Get thumbnail URL from links
        thumbnail_url = None
        preview_url = None
        for link in item.get("links", []):
            if link.get("rel") == "preview":
                preview_url = link.get("href")
                thumbnail_url = preview_url  # Use preview as thumbnail
                break
        
        images.append(NASAImage(
            nasa_id=item_data.get("nasa_id", ""),
            title=item_data.get("title", "Untitled"),
            description=item_data.get("description", "")[:500],  # Truncate long descriptions
            date_created=item_data.get("date_created", ""),
            center=item_data.get("center", ""),
            keywords=item_data.get("keywords", [])[:10],  # Limit keywords
            thumbnail_url=thumbnail_url,
            preview_url=preview_url
        ))
    
    return images


async def get_image_variants(nasa_id: str) -> list[str]:
    """
    Get all image variants (sizes) for a NASA image.
    
    Args:
        nasa_id: The NASA ID of the image
        
    Returns:
        List of URLs for different image sizes
    """
    # First, we need to find the collection URL from a search
    url = f"{NASA_API_BASE}/asset/{nasa_id}"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            
            # Extract URLs from the collection
            items = data.get("collection", {}).get("items", [])
            return [item.get("href", "") for item in items if item.get("href")]
        except Exception:
            return []


def format_image_for_display(image: NASAImage) -> str:
    """Format a NASA image for text display."""
    keywords = ", ".join(image.keywords[:5]) if image.keywords else "None"
    return f"""
📸 **{image.title}**
- NASA ID: {image.nasa_id}
- Date: {image.date_created[:10] if image.date_created else 'Unknown'}
- Center: {image.center or 'Unknown'}
- Keywords: {keywords}
- Description: {image.description[:200]}{'...' if len(image.description) > 200 else ''}
"""


def format_images_summary(images: list[NASAImage], max_images: int = 5) -> str:
    """Format multiple images as a summary for agent prompts."""
    if not images:
        return "No images found."
    
    lines = []
    for i, img in enumerate(images[:max_images], 1):
        keywords = ", ".join(img.keywords[:3]) if img.keywords else "none"
        lines.append(f"{i}. [{img.nasa_id}] {img.title}")
        lines.append(f"   Keywords: {keywords}")
        lines.append(f"   Description: {img.description[:150]}...")
        lines.append("")
    
    return "\n".join(lines)
