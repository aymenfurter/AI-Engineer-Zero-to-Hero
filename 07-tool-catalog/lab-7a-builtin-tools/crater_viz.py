"""
Asteroid Impact Visualization (Animated Dark Mode)
"""
from IPython.display import HTML, display
import uuid

def visualize_crater(agent_km: float, validation: dict) -> None:
    """
    Visualize crater diameter comparison with animation (dark mode).
    """
    vid = uuid.uuid4().hex[:8]
    expected_km = validation.get("expected", agent_km)
    
    # Scale: max diameter maps to 350px width
    width_px = 380
    max_d = max(agent_km, expected_km) * 1.2
    scale = width_px / max_d
    
    a_width = agent_km * scale
    e_width = expected_km * scale
    
    # Calculate error for display
    error_pct = abs(agent_km - expected_km) / expected_km * 100 if expected_km else 0
    
    html = f'''
<style>
    @keyframes growBar_{vid} {{
        0% {{ width: 0; opacity: 0; }}
        100% {{ width: var(--target-width); opacity: 1; }}
    }}
    @keyframes fadeIn_{vid} {{
        0% {{ opacity: 0; transform: translateY(12px); }}
        100% {{ opacity: 1; transform: translateY(0); }}
    }}
    .crater-container-{vid} {{
        font-family: 'Poppins', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        background: linear-gradient(145deg, #0A192F 0%, #112240 100%);
        padding: 28px 32px;
        border-radius: 16px;
        border: 1px solid rgba(100, 255, 218, 0.1);
        max-width: 480px;
        animation: fadeIn_{vid} 0.6s ease-out;
        box-shadow: 0 10px 40px -10px rgba(2, 12, 27, 0.7);
    }}
    .crater-header-{vid} {{
        margin-bottom: 28px;
        padding-bottom: 20px;
        border-bottom: 1px solid rgba(100, 255, 218, 0.1);
    }}
    .crater-title-{vid} {{
        margin: 0;
        color: #CCD6F6;
        font-size: 18px;
        font-weight: 600;
        letter-spacing: -0.01em;
    }}
    .crater-subtitle-{vid} {{
        margin: 4px 0 0 0;
        color: #64FFDA;
        font-family: 'Fira Code', 'SF Mono', Monaco, monospace;
        font-size: 12px;
        font-weight: 400;
        letter-spacing: 0.02em;
    }}
    .bar-section-{vid} {{
        margin-bottom: 20px;
        animation: fadeIn_{vid} 0.7s ease-out backwards;
    }}
    .bar-section-{vid}:nth-child(2) {{ animation-delay: 0.15s; }}
    .bar-section-{vid}:nth-child(3) {{ animation-delay: 0.3s; }}
    .bar-label-{vid} {{
        color: #8892B0;
        font-size: 13px;
        font-weight: 500;
        margin-bottom: 10px;
        display: flex;
        justify-content: space-between;
        align-items: baseline;
    }}
    .bar-label-name-{vid} {{
        display: flex;
        align-items: center;
        gap: 8px;
    }}
    .bar-label-name-{vid}::before {{
        content: '→';
        color: #64FFDA;
        font-family: 'Fira Code', monospace;
        font-size: 11px;
    }}
    .bar-value-{vid} {{
        color: #CCD6F6;
        font-weight: 600;
        font-family: 'Fira Code', 'SF Mono', Monaco, monospace;
        font-size: 14px;
    }}
    .bar-track-{vid} {{
        background: rgba(100, 255, 218, 0.05);
        border-radius: 8px;
        height: 32px;
        overflow: hidden;
        position: relative;
        border: 1px solid rgba(100, 255, 218, 0.08);
    }}
    .bar-fill-agent-{vid} {{
        --target-width: {a_width}px;
        height: 100%;
        background: linear-gradient(90deg, #f97316, #fb923c);
        border-radius: 7px;
        animation: growBar_{vid} 1s cubic-bezier(0.4, 0, 0.2, 1) 0.3s forwards;
        width: 0;
        box-shadow: 0 0 20px rgba(249, 115, 22, 0.3);
    }}
    .bar-fill-expected-{vid} {{
        --target-width: {e_width}px;
        height: 100%;
        background: linear-gradient(90deg, #64FFDA, #5eead4);
        border-radius: 7px;
        animation: growBar_{vid} 1s cubic-bezier(0.4, 0, 0.2, 1) 0.5s forwards;
        width: 0;
        box-shadow: 0 0 20px rgba(100, 255, 218, 0.3);
    }}
    .legend-{vid} {{
        display: flex;
        gap: 24px;
        margin-top: 24px;
        padding-top: 20px;
        border-top: 1px solid rgba(100, 255, 218, 0.1);
        animation: fadeIn_{vid} 0.7s ease-out 0.6s backwards;
    }}
    .legend-item-{vid} {{
        display: flex;
        align-items: center;
        gap: 10px;
        font-size: 12px;
        color: #8892B0;
        font-weight: 500;
    }}
    .legend-dot-agent-{vid} {{
        width: 14px;
        height: 14px;
        background: linear-gradient(135deg, #f97316, #fb923c);
        border-radius: 4px;
        box-shadow: 0 2px 8px rgba(249, 115, 22, 0.3);
    }}
    .legend-dot-expected-{vid} {{
        width: 14px;
        height: 14px;
        background: linear-gradient(135deg, #64FFDA, #5eead4);
        border-radius: 4px;
        box-shadow: 0 2px 8px rgba(100, 255, 218, 0.3);
    }}
    .comparison-{vid} {{
        margin-top: 16px;
        font-size: 13px;
        color: #8892B0;
        font-family: 'Fira Code', 'SF Mono', Monaco, monospace;
        animation: fadeIn_{vid} 0.7s ease-out 0.8s backwards;
        padding: 12px 16px;
        background: rgba(100, 255, 218, 0.03);
        border-radius: 8px;
        border: 1px solid rgba(100, 255, 218, 0.06);
    }}
    .comparison-{vid} strong {{
        color: #CCD6F6;
    }}
    .result-badge-{vid} {{
        margin-top: 20px;
        padding: 14px 20px;
        border-radius: 8px;
        font-size: 14px;
        font-weight: 600;
        display: flex;
        align-items: center;
        gap: 12px;
        animation: fadeIn_{vid} 0.7s ease-out 1s backwards;
        letter-spacing: 0.01em;
    }}
    .result-valid-{vid} {{
        background: rgba(100, 255, 218, 0.1);
        border: 1px solid rgba(100, 255, 218, 0.25);
        color: #64FFDA;
    }}
    .result-invalid-{vid} {{
        background: rgba(255, 107, 107, 0.1);
        border: 1px solid rgba(255, 107, 107, 0.25);
        color: #ff6b6b;
    }}
    .result-icon-{vid} {{
        font-size: 18px;
    }}
</style>

<div class="crater-container-{vid}">
    <div class="crater-header-{vid}">
        <h3 class="crater-title-{vid}">Crater Impact Analysis</h3>
        <p class="crater-subtitle-{vid}">diameter comparison</p>
    </div>
    
    <div class="bar-section-{vid}">
        <div class="bar-label-{vid}">
            <span class="bar-label-name-{vid}">Agent Result</span>
            <span class="bar-value-{vid}">{agent_km:.2f} km</span>
        </div>
        <div class="bar-track-{vid}">
            <div class="bar-fill-agent-{vid}"></div>
        </div>
    </div>
    
    <div class="bar-section-{vid}">
        <div class="bar-label-{vid}">
            <span class="bar-label-name-{vid}">Expected (Physics)</span>
            <span class="bar-value-{vid}">{expected_km:.2f} km</span>
        </div>
        <div class="bar-track-{vid}">
            <div class="bar-fill-expected-{vid}"></div>
        </div>
    </div>
    
    <div class="legend-{vid}">
        <div class="legend-item-{vid}">
            <div class="legend-dot-agent-{vid}"></div>
            <span>AI Agent</span>
        </div>
        <div class="legend-item-{vid}">
            <div class="legend-dot-expected-{vid}"></div>
            <span>Physics Model</span>
        </div>
    </div>
    
    <div class="comparison-{vid}">
        Δ <strong>{abs(agent_km - expected_km):.3f} km</strong> · {error_pct:.1f}% {'under' if agent_km < expected_km else 'over'}estimate
    </div>
    
    <div class="result-badge-{vid} {'result-valid-' + vid if validation['valid'] else 'result-invalid-' + vid}">
        <span class="result-icon-{vid}">{'✓' if validation['valid'] else '✗'}</span>
        {'Verified — within 10% tolerance' if validation['valid'] else f"Mismatch — {validation['error_percent']:.1f}% exceeds threshold"}
    </div>
</div>
'''
    display(HTML(html))
