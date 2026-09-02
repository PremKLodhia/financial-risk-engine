import math

def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points on the Earth in kilometres."""
    if lat1 == lat2 and lon1 == lon2:
        return 0.0
    
    R = 6371.0  # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2.0) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

def calculate_implied_speed_kmh(dist_km: float, time_delta_seconds: float) -> float:
    """Calculates speed required to travel distance in given time."""
    if time_delta_seconds <= 0:
        return 0.0 if dist_km == 0.0 else 99999.0
    hours = time_delta_seconds / 3600.0
    return dist_km / hours
