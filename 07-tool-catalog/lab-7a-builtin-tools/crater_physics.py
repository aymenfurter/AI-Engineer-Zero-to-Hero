"""
Asteroid Impact Physics - Validation Functions (Simplified)
"""
import math

# Constants
G = 9.81
RHO_TARGET = 2500

def calculate_crater_diameter(diameter_m: float, velocity_km_s: float, density_kg_m3: float = 2700, angle_deg: float = 45) -> float:
    """Calculate crater diameter using Pi-scaling law (Holsapple 1993)."""
    velocity_m_s = velocity_km_s * 1000
    angle_rad = math.radians(angle_deg)
    
    # Holsapple approximation
    diameter_km = (
        1.161 
        * (density_kg_m3 / RHO_TARGET)**0.33 
        * diameter_m**0.78 
        * velocity_m_s**0.44 
        * G**(-0.22) 
        * math.sin(angle_rad)**0.33
    ) / 1000
    
    return diameter_km

def validate_crater(agent_crater_km: float, diameter_m: float, velocity_km_s: float) -> dict:
    """Validate agent's crater calculation."""
    expected_km = calculate_crater_diameter(diameter_m, velocity_km_s)
    
    if agent_crater_km <= 0:
        return {"valid": False, "error": "Invalid result"}
        
    error_pct = abs(agent_crater_km - expected_km) / expected_km * 100
    return {
        "valid": error_pct <= 10,
        "expected": expected_km,
        "actual": agent_crater_km,
        "error_percent": error_pct
    }
