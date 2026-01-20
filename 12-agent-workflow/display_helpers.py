"""Display helpers for the NASA slideshow workflow."""
from typing import Optional
from IPython.display import display, HTML, Markdown, clear_output
import json


def display_outline(outline: dict) -> None:
    """Display the presentation outline in a formatted way."""
    html = f"""
    <div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); 
                padding: 20px; border-radius: 12px; color: white; margin: 10px 0;">
        <h2 style="margin: 0 0 10px 0; color: #e94560;">📋 {outline['title']}</h2>
        <p style="color: #a0a0a0; font-style: italic; margin-bottom: 20px;">{outline['narrative']}</p>
        <h4 style="color: #0f3460; background: #e94560; padding: 5px 10px; border-radius: 4px; display: inline-block;">
            Slides ({len(outline['slides'])})
        </h4>
    """
    
    for slide in outline['slides']:
        keywords = ', '.join(slide.get('search_keywords', [])[:3])
        html += f"""
        <div style="background: rgba(255,255,255,0.05); padding: 12px; margin: 8px 0; border-radius: 8px; border-left: 3px solid #e94560;">
            <strong style="color: #e94560;">#{slide['position']}</strong> 
            <span style="color: #fff;">{slide['subject']}</span> — 
            <span style="color: #a0a0a0;">{slide['topic']}</span>
            <br>
            <small style="color: #666;">🔍 {keywords}</small>
        </div>
        """
    
    html += "</div>"
    display(HTML(html))


def display_search_results(query: str, candidates: list[dict]) -> None:
    """Display search results from NASA API."""
    html = f"""
    <div style="background: #1e1e2e; padding: 15px; border-radius: 8px; margin: 10px 0;">
        <h4 style="color: #89b4fa; margin: 0 0 10px 0;">🔍 Search: "{query}"</h4>
        <p style="color: #a6adc8; margin-bottom: 10px;">Found {len(candidates)} candidates</p>
    """
    
    for img in candidates[:5]:
        thumb = img.get('thumbnail_url', '')
        thumb_html = f'<img src="{thumb}" style="width: 80px; height: 60px; object-fit: cover; border-radius: 4px; margin-right: 10px;">' if thumb else ''
        
        html += f"""
        <div style="display: flex; align-items: center; background: rgba(255,255,255,0.05); 
                    padding: 8px; margin: 5px 0; border-radius: 6px;">
            {thumb_html}
            <div>
                <strong style="color: #cdd6f4;">{img.get('title', 'Untitled')[:50]}</strong>
                <br>
                <small style="color: #6c7086;">ID: {img.get('nasa_id', 'N/A')}</small>
            </div>
        </div>
        """
    
    html += "</div>"
    display(HTML(html))


def display_selection(nasa_id: str, title: str, reason: str, thumbnail_url: Optional[str] = None) -> None:
    """Display the selected image."""
    thumb_html = f'<img src="{thumbnail_url}" style="max-width: 200px; border-radius: 8px; margin-bottom: 10px;">' if thumbnail_url else ''
    
    html = f"""
    <div style="background: #1e3a1e; padding: 15px; border-radius: 8px; margin: 10px 0; border-left: 4px solid #50fa7b;">
        <h4 style="color: #50fa7b; margin: 0 0 10px 0;">✅ Selected Image</h4>
        {thumb_html}
        <p style="color: #fff; margin: 5px 0;"><strong>{title}</strong></p>
        <p style="color: #a6adc8; font-size: 0.9em;">ID: {nasa_id}</p>
        <p style="color: #94e2d5; font-size: 0.9em;">💡 {reason}</p>
    </div>
    """
    display(HTML(html))


def display_review(approved: bool, feedback: str, issues: list[str] = None) -> None:
    """Display the review result."""
    if approved:
        html = f"""
        <div style="background: #1e3a1e; padding: 12px; border-radius: 8px; margin: 10px 0;">
            <span style="color: #50fa7b; font-size: 1.2em;">✅ APPROVED</span>
            <p style="color: #a6adc8; margin: 5px 0;">{feedback}</p>
        </div>
        """
    else:
        issues_html = ''.join([f'<li style="color: #f38ba8;">{issue}</li>' for issue in (issues or [])])
        html = f"""
        <div style="background: #3a1e1e; padding: 12px; border-radius: 8px; margin: 10px 0;">
            <span style="color: #f38ba8; font-size: 1.2em;">❌ REJECTED</span>
            <p style="color: #a6adc8; margin: 5px 0;">{feedback}</p>
            <ul style="margin: 5px 0;">{issues_html}</ul>
        </div>
        """
    display(HTML(html))


def display_slide_progress(position: int, total: int, subject: str, topic: str) -> None:
    """Display current slide progress."""
    progress_pct = (position / total) * 100
    
    html = f"""
    <div style="background: #1e1e2e; padding: 15px; border-radius: 8px; margin: 10px 0;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
            <span style="color: #cdd6f4; font-size: 1.1em;">🚀 Slide {position}/{total}</span>
            <span style="color: #f9e2af;">{subject}</span>
        </div>
        <div style="background: #313244; border-radius: 4px; height: 8px; overflow: hidden;">
            <div style="background: linear-gradient(90deg, #89b4fa, #cba6f7); height: 100%; width: {progress_pct}%;"></div>
        </div>
        <p style="color: #6c7086; margin-top: 10px; font-size: 0.9em;">Topic: {topic}</p>
    </div>
    """
    display(HTML(html))


def display_final_slideshow(slideshow: dict) -> None:
    """Display the complete slideshow."""
    html = f"""
    <div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); 
                padding: 25px; border-radius: 16px; color: white; margin: 20px 0;">
        <h1 style="margin: 0 0 10px 0; color: #f9e2af; text-align: center;">🚀 {slideshow['title']}</h1>
        <p style="color: #a0a0a0; text-align: center; font-style: italic; margin-bottom: 30px;">
            {slideshow['narrative']}
        </p>
        <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 15px;">
    """
    
    for slide in slideshow['slides']:
        thumb = slide.get('thumbnail_url', '')
        thumb_html = f'<img src="{thumb}" style="width: 100%; height: 150px; object-fit: cover; border-radius: 8px 8px 0 0;">' if thumb else '<div style="height: 150px; background: #313244; border-radius: 8px 8px 0 0;"></div>'
        
        html += f"""
        <div style="background: rgba(255,255,255,0.05); border-radius: 8px; overflow: hidden;">
            {thumb_html}
            <div style="padding: 12px;">
                <div style="color: #e94560; font-size: 0.8em; margin-bottom: 5px;">
                    #{slide['position']} • {slide['subject']}
                </div>
                <div style="color: #fff; font-weight: bold; margin-bottom: 5px;">
                    {slide['topic'][:40]}
                </div>
                <div style="color: #6c7086; font-size: 0.85em;">
                    {slide['image']['title'][:50]}...
                </div>
            </div>
        </div>
        """
    
    html += """
        </div>
        <div style="text-align: center; margin-top: 25px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.1);">
            <span style="color: #50fa7b; font-size: 1.2em;">✨ Slideshow Complete!</span>
            <p style="color: #6c7086;">Total slides: """ + str(len(slideshow['slides'])) + """</p>
        </div>
    </div>
    """
    display(HTML(html))


def display_event(event: dict) -> None:
    """Display a workflow event (for debugging/demonstration)."""
    event_type = event.get('type', 'unknown')
    
    colors = {
        'search_started': '#89b4fa',
        'search_completed': '#89dceb',
        'selection_started': '#f9e2af',
        'image_selected': '#a6e3a1',
        'review_started': '#cba6f7',
        'review_completed': '#f5c2e7',
        'judge_started': '#fab387',
        'judge_selected': '#94e2d5',
        'slide_complete': '#50fa7b',
        'error': '#f38ba8'
    }
    
    color = colors.get(event_type, '#6c7086')
    
    # Format event data
    data_items = []
    for k, v in event.items():
        if k != 'type':
            if isinstance(v, (dict, list)):
                v = json.dumps(v)[:100] + '...' if len(str(v)) > 100 else str(v)
            data_items.append(f"<small style='color: #a6adc8;'>{k}: {v}</small>")
    
    data_html = '<br>'.join(data_items[:4])
    
    html = f"""
    <div style="background: #1e1e2e; padding: 8px 12px; margin: 3px 0; border-radius: 4px; 
                border-left: 3px solid {color}; font-family: monospace;">
        <span style="color: {color}; font-weight: bold;">{event_type}</span>
        <br>
        {data_html}
    </div>
    """
    display(HTML(html))
