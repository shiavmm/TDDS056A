import math
from typing import List, Optional, Dict, Any

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points on the Earth's surface
    specified in decimal degrees (latitude/longitude).
    Returns the distance in kilometers.
    """
    # Earth radius in kilometers
    R = 6371.0

    # Convert coordinates from degrees to radians
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    # Haversine formula
    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return R * c

def match_trip_to_request(trip: Any, request: Any, max_distance_km: float = 2.0) -> Optional[Dict[str, Any]]:
    """
    Evaluates if a driver's trip route matches a passenger's pickup and dropoff requirements.
    
    A match is valid if:
    1. The trip status is 'scheduled' or 'active'.
    2. The trip has enough available seats for the request.
    3. There exist waypoints i and j in the trip's route such that:
       - Waypoint i matches the passenger's pickup (distance <= max_distance_km)
       - Waypoint j matches the passenger's dropoff (distance <= max_distance_km)
       - Waypoint i occurs BEFORE Waypoint j in the sequence (sequence_i < sequence_j)
       
    Returns a dictionary of match details (including closest distances and matched sequences) if valid,
    otherwise returns None.
    """
    # Check seat availability and trip state
    if trip.status not in ["scheduled", "active"]:
        return None
    if trip.available_seats < request.requested_seats:
        return None
    
    # Sort the waypoints by sequence order to ensure chronological navigation
    waypoints = sorted(trip.route.waypoints, key=lambda wp: wp.sequence)
    n = len(waypoints)
    
    best_match = None
    min_combined_distance = float("inf")
    
    # Check all pairs (i, j) where i < j (pickup sequence before dropoff sequence)
    for i in range(n):
        wp_pickup = waypoints[i]
        dist_pickup = haversine_distance(
            wp_pickup.latitude, wp_pickup.longitude,
            request.pickup_latitude, request.pickup_longitude
        )
        
        # If pickup waypoint is too far, skip it
        if dist_pickup > max_distance_km:
            continue
            
        for j in range(i + 1, n):
            wp_dropoff = waypoints[j]
            dist_dropoff = haversine_distance(
                wp_dropoff.latitude, wp_dropoff.longitude,
                request.dropoff_latitude, request.dropoff_longitude
            )
            
            # If dropoff waypoint is too far, skip it
            if dist_dropoff > max_distance_km:
                continue
                
            # If this is a valid match, let's see if it's the closest overall pair
            combined_distance = dist_pickup + dist_dropoff
            if combined_distance < min_combined_distance:
                min_combined_distance = combined_distance
                best_match = {
                    "trip": trip,
                    "pickup_distance_km": round(dist_pickup, 3),
                    "dropoff_distance_km": round(dist_dropoff, 3),
                    "pickup_waypoint_seq": wp_pickup.sequence,
                    "dropoff_waypoint_seq": wp_dropoff.sequence
                }
                
    return best_match
